"""
Env for Kastan: openai_3
"""

import inspect
import os
import traceback
from typing import List, Sequence, Tuple

import langchain
# from ai_ta_backend.agents import get_docstore_agent
from dotenv import load_dotenv
from github import GithubException
from github.Issue import Issue
from langchain.agents import (AgentExecutor, AgentType, Tool, initialize_agent,
                              load_tools)
from langchain.agents.agent_toolkits import PlayWrightBrowserToolkit
from langchain.agents.agent_toolkits.github.toolkit import GitHubToolkit
from langchain.agents.openai_functions_multi_agent.base import \
    OpenAIMultiFunctionsAgent
from langchain.agents.react.base import DocstoreExplorer
from langchain.callbacks.manager import tracing_v2_enabled
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.chat_models.base import BaseChatModel
from langchain.docstore.base import Docstore
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.memory import (ConversationBufferMemory,
                              ConversationSummaryBufferMemory)
from langchain.prompts import (ChatPromptTemplate, HumanMessagePromptTemplate,
                               MessagesPlaceholder, PromptTemplate)
from langchain.prompts.chat import (BaseMessagePromptTemplate,
                                    ChatPromptTemplate,
                                    HumanMessagePromptTemplate,
                                    MessagesPlaceholder,
                                    SystemMessagePromptTemplate)
from langchain.schema import AgentAction
from langchain.schema.language_model import BaseLanguageModel
from langchain.schema.messages import (AIMessage, BaseMessage, FunctionMessage,
                                       SystemMessage)
from langchain.tools.base import BaseTool
from langchain.tools.playwright.utils import \
    create_sync_playwright_browser  # A synchronous browser is available, though it isn't compatible with jupyter.
from langchain.tools.playwright.utils import create_async_playwright_browser
from langchain.utilities.github import GitHubAPIWrapper
from langchain.vectorstores import Qdrant
# from langchain_experimental.autonomous_agents.autogpt.agent import AutoGPT
# from langchain_experimental.autonomous_agents.baby_agi import BabyAGI
from langchain_experimental.plan_and_execute.agent_executor import \
    PlanAndExecute
from langchain_experimental.plan_and_execute.executors.agent_executor import \
    load_agent_executor
from langchain_experimental.plan_and_execute.planners.chat_planner import \
    load_chat_planner
from qdrant_client import QdrantClient
from typing_extensions import runtime

from ai_ta_backend.agents.tools import (get_human_input, get_shell_tool,
                                        get_tools)

# load_dotenv(override=True, dotenv_path='.env')

os.environ["LANGCHAIN_TRACING"] = "true"  # If you want to trace the execution of the program, set to "true"
os.environ["LANGCHAIN_WANDB_TRACING"] = "true"  # TODO: https://docs.wandb.ai/guides/integrations/langchain
os.environ["WANDB_PROJECT"] = "langchain-tracing"  # optionally set your wandb settings or configs
# os.environ["LANGCHAIN_TRACING"] = "false"  # If you want to trace the execution of the program, set to "true"
# os.environ["LANGCHAIN_WANDB_TRACING"] = "false"  # TODO: https://docs.wandb.ai/guides/integrations/langchain
# os.environ["WANDB_PROJECT"] = ""  # optionally set your wandb settings or configs

langchain.debug = False  # True for more detailed logs
VERBOSE = True

from ai_ta_backend.agents.outer_loop_planner import \
    fancier_trim_intermediate_steps

GH_Agent_SYSTEM_PROMPT = """You are a senior developer who helps others finish the work faster and to a higher quality than anyone else on the team. People often tag you on pull requests (PRs), and you will finish the PR to the best of your ability and commit your changes. If you're blocked or stuck, feel free to leave a comment on the PR and the rest of the team will help you out. Remember to keep trying, and reflecting on how you solved previous problems will usually help you fix the current issue. Please work hard, stay organized, and follow best practices.\nYou have access to the following tools:"""


class GH_Agent():

  def __init__(self, branch_name: str = ''):
    self.branch_name = branch_name
    self.github_api_wrapper = GitHubAPIWrapper(active_branch=branch_name, github_base_branch='main')  # type: ignore
    self.pr_agent: AgentExecutor = self.make_bot()

  def make_bot(self):
    # LLMs
    SystemMessage(content=GH_Agent_SYSTEM_PROMPT)

    llm = ChatOpenAI(temperature=0, model="gpt-4-0613", max_retries=3, request_timeout=60 * 3)  # type: ignore
    human_llm = ChatOpenAI(temperature=0, model="gpt-4-0613", max_retries=3, request_timeout=60 * 3)  # type: ignore
    summarizer_llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613", max_retries=3, request_timeout=60 * 3)  # type: ignore
    # MEMORY
    chat_history = MessagesPlaceholder(variable_name="chat_history")
    memory = ConversationSummaryBufferMemory(memory_key="chat_history", return_messages=True, llm=summarizer_llm, max_token_limit=2_000)

    # TOOLS
    toolkit: GitHubToolkit = GitHubToolkit.from_github_api_wrapper(self.github_api_wrapper)
    github_tools: list[BaseTool] = toolkit.get_tools()
    human_tools: List[BaseTool] = load_tools(["human"], llm=human_llm, input_func=get_human_input)
    # todo: add tools for documentation search... unless I have a separate code author.
    # todo: tool for human. Maybe Arxiv too.

    return initialize_agent(
        tools=github_tools + human_tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        # agent=AgentType.OPENAI_MULTI_FUNCTIONS,
        verbose=VERBOSE,
        handle_parsing_errors=True,  # or pass a function that accepts the error and returns a string
        max_iterations=30,
        max_execution_time=None,
        early_stopping_method='generate',
        memory=memory,
        trim_intermediate_steps=fancier_trim_intermediate_steps,
        agent_kwargs={
            "memory_prompts": [chat_history],
            "input_variables": ["input", "agent_scratchpad", "chat_history"],
            "prefix": GH_Agent_SYSTEM_PROMPT,
            # pretty sure this is wack: # "extra_prompt_messages": [MessagesPlaceholder(variable_name="GH_Agent_SYSTEM_PROMPT")] 
        })

  def launch_gh_agent(self, instruction: str, active_branch='bot-branch'):
    # self.github_api_wrapper.set_active_branch(active_branch)
    return self.bot_runner_with_retries(self.pr_agent, instruction)

  def bot_runner_with_retries(self, bot: AgentExecutor, run_instruction, total_retries=1):
    """Runs the given bot with attempted retries. First prototype.
    """  

    print("LIMITING TOTAL RETRIES TO 0, wasting too much money....")
    runtime_exceptions = []
    result = ''
    for num_retries in range(1,total_retries+1):
      warning_to_bot = f"Keep in mind the last bot that tried to solve this problem faced a runtime error. Please learn from the mistakes of the last bot. The last bot's error was: {str(runtime_exceptions)}"
      if len(runtime_exceptions) > 1:
        warning_to_bot = f"Keep in mind {num_retries} previous bots have tried to solve this problem faced a runtime error. Please learn from their mistakes, focus on making sure you format your requests for tool use correctly. Here's a list of their previous runtime errors: {str(runtime_exceptions)}"
      
      try:
          with tracing_v2_enabled(project_name="Github Agent Dev"):
            result = bot.run(f"{run_instruction}\n{warning_to_bot}")
          break # no error, so break retry loop
      except Exception as e:
          print("-----------❌❌❌❌------------START OF ERROR-----------❌❌❌❌------------")
          print(f"Error in {inspect.currentframe().f_code.co_name}: {e}") # print function name in error.
          print(f"Traceback:")
          print(traceback.print_exc())

          runtime_exceptions.append(traceback.format_exc())
          print(f"❌❌❌ num_retries: {num_retries}. Bot hit runtime exception: {e}")
    if result == '':
      result = f"{total_retries} agents ALL FAILED with runtime exceptions: runtime_exceptions: {runtime_exceptions}"
    print(f"👇FINAL ANSWER 👇\n{result}")
    return result


def generate_branch_name(issue: Issue):
  """Generate a meaningful branch name that the Agent will use to commit it's new code against. Later, it can use this branch to open a pull request."""
  system_template = "You are a helpful assistant that writes clear and concise GitHub branch names for new pull requests."
  system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
  example_issue = {"title": "Implement an Integral function in C", "body": "This request includes a placeholder for a C program that calculates an integral and a Makefile to compile it. Closes issue #6."}

  prompt = HumanMessagePromptTemplate.from_template(
      '''Given this issue, please return a single string that would be a suitable branch name on which to implement this feature request. Use common software development best practices to name the branch.
    Follow this formatting exactly:
    Issue: {example_issue}
    Branch name: `add_integral_in_c`


    Issue: {issue}
    Branch name: `''')

  # Combine into a Chat conversation
  chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, prompt])
  formatted_messages = chat_prompt.format_messages(issue=str(issue), example_issue=str(example_issue))

  llm = ChatOpenAI(temperature=0, model="gpt-4-0613", max_retries=3, request_timeout=60 * 3)  # type: ignore
  output = llm(formatted_messages)
  print(f"SUGGESTED_BRANCH_NAME: <<{output.content}>>")
  print(f"Cleaned branch name: <<{sanitize_branch_name(output.content)}>>")

  return ensure_unique_branch_name(issue.repository, sanitize_branch_name(output.content))


def sanitize_branch_name(text):
  """
  # Remove non-alphanumeric characters, use underscores. 
  Example:
    cleaned_text = strip_n_clean_text("Hello, World! This is an example.")
    print(cleaned_text)  # Output: "Hello_World_This_is_an_example"

  Returns:
      str: cleaned_text
  """
  cleaned_words = [''.join(c for c in word if c.isalnum() or c == '_') for word in text.split()]
  return '_'.join(cleaned_words)

def ensure_unique_branch_name(repo, proposed_branch_name):
  # Attempt to create the branch, appending _v{i} if the name already exists
  i = 0
  new_branch_name = proposed_branch_name
  base_branch = repo.get_branch(repo.default_branch)
  while True:
    try:
      repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=base_branch.commit.sha)
      print(f"Branch '{new_branch_name}' created successfully!")
      return new_branch_name
    except GithubException as e:
      if e.status == 422 and "Reference already exists" in e.data['message']:
        i += 1
        new_branch_name = f"{proposed_branch_name}_v{i}"
        print(f"Branch name already exists. Trying with {new_branch_name}...")
      else:
        # Handle any other exceptions
        print(f"Failed to create branch. Error: {e}")
        raise Exception(f"Unable to create branch name from proposed_branch_name: {proposed_branch_name}")


if __name__ == "__main__":
  print("No code.")