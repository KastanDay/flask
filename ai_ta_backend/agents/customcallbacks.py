from typing import Dict, Union, Any, List
import os

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import AgentType, initialize_agent, load_tools
from langchain.callbacks import tracing_enabled
from langchain.llms import OpenAI
from langchain import hub
from ai_ta_backend.agents.utils import SupabaseDB, get_langsmith_id
import marvin
from marvin import ai_model
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv(override=True, dotenv_path='.env')

marvin.settings.openai.api_key = os.getenv('OPENAI_API_KEY')
@ai_model
class AgentActionParser(BaseModel):
    log: str = Field(..., description="clean logs information from input, without new line breaks and markdowns")
    action: str = Field(..., description="parse action field from logs")
    action_input: str = Field(..., description="parse action input from logs")
    action_output: str = Field(..., description="parse action output from logs")
    tool: str = Field(..., description="any tool information from input")
    tool_input: str = Field(..., description="any tool input")
    tool_output: str = Field(..., description="parse tool output")

class CustomCallbackHandler(BaseCallbackHandler):
    """A callback handler that stores the LLM's context and action in memory."""
    def __init__(self, run_id=None, image_name=None):
        if run_id:
            self.langsmith_run_id = run_id
        else:
            self.langsmith_run_id = get_langsmith_id()

        if image_name:
            self.image_name = image_name
        else:
            self.image_name = ''

        self.tool_in_progress = {"status": False, "name": ""}
        self.db = SupabaseDB(table_name="docker_images", image_name=self.image_name)


    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        """Callback for when a tool starts.
        Set tool_in_progress to True and store the tool's name in memory."""
        self.tool_in_progress['status'] = True
        self.tool_in_progress['name'] = serialized['name']

        if self.db.is_exists_image():
            data = self.db.fetch_field_from_db("on_tool_start")
            if data:
                data.append(serialized)
                response = self.db.update_field_in_db("on_tool_start", data)
            else:
                response = self.db.update_field_in_db("on_tool_start", [serialized])
        else:
            response = self.db.upsert_field_in_db("on_tool_start", [serialized])



    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Callback for when a tool ends.
        Use this to store the tool's output in a database. Use tool start parameters to identify the tool."""
        if self.tool_in_progress['status']:
            tool_name = self.tool_in_progress['name']
            output = {"name": tool_name, "output": output}
            # reset tool_in_progress
            self.tool_in_progress['status'] = False
            self.tool_in_progress['name'] = ''

        if self.db.is_exists_image():
            data = self.db.fetch_field_from_db("on_tool_end")
            if data:
                data.append(output)
                response = self.db.update_field_in_db("on_tool_end", data)
            else:
                response = self.db.update_field_in_db("on_tool_end", [output])
        else:
            response = self.db.upsert_field_in_db("on_tool_end", [output])


    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        """Run when LLM errors."""
        pass

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        """Run when LLM errors."""
        pass

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Run when LLM predicts an action. Parse the action and store it in a database."""
        action = action.dict()
        parsed_action = AgentActionParser(action)
        action_data = {"log": parsed_action.log, "action": parsed_action.action, "action_input": parsed_action.action_input,
                       "action_output": parsed_action.action_output, "tool": parsed_action.tool,
                       "tool_input": parsed_action.tool_input, "tool_output": parsed_action.tool_output}

        if self.db.is_exists_image():
            data = self.db.fetch_field_from_db("on_agent_action")
            if data:
                data.append(action_data)
                response = self.db.update_field_in_db("on_agent_action", data)
            else:
                response = self.db.update_field_in_db("on_agent_action", [action_data])
        else:
            response = self.db.upsert_field_in_db("on_agent_action", [action_data])

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        """Run when LLM finishes. Store the finish in a database."""
        finish = finish.dict()

        if self.db.is_exists_image():
            data = self.db.fetch_field_from_db("on_agent_finish")
            if data:
                data.append(finish)
                response = self.db.update_field_in_db("on_agent_finish", data)
            else:
                response = self.db.update_field_in_db("on_agent_finish", finish)
        else:
            response = self.db.upsert_field_in_db("on_agent_finish", finish)


    # def agent_output():
    # TODO
    # missing agent output in db


    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> Any:
        """Callback for when a chain starts."""
        pass



if __name__ == "__main__":
    # for testing
    handler1 = CustomCallbackHandler()

    memory_prompt = hub.pull("kastanday/memory_manager_agent")

    llm = OpenAI(temperature=0, streaming=True)
    tools = load_tools(["llm-math"], llm=llm)
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)

    # Callbacks for handler1 will be issued by every object involved in the
    # Agent execution (llm, llmchain, tool, agent executor)
    agent.run("What is 2 raised to the 0.235 power?", callbacks=[handler1])
