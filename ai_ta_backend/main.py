import newrelic.agent

newrelic.agent.initialize('newrelic.ini')


import logging
import os
import re
import time
from typing import Any, List, Union

import ray
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from h11 import Response
from regex import D
# from qdrant_client import QdrantClient
from sqlalchemy import JSON

from ai_ta_backend.vector_database import Ingest
from ai_ta_backend.web_scrape import main_crawler, mit_course_download

app = Flask(__name__)
CORS(app)

# load API keys from globally-availabe .env file
load_dotenv(dotenv_path='.env', override=True)

# NewRelic logging

metadata = {'startup time': time.time(), 'int val': 2}
logging.info("Starting up server (separate metadata)", metadata)
logging.info(f"Starting up server (fstring metadata): {metadata}")
# logging.info("Starting up server (metadata=metadata):", metadata=metadata)

# import structlog

# # Configure structlog to output structured logs in JSON format 
# structlog.configure( 
# processors=[ structlog.stdlib.filter_by_level, structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer() 
# ], 
# context_class=dict, logger_factory=structlog.stdlib.LoggerFactory(), 
# )
# # Get a logger 
# logger = structlog.get_logger() 
# # Now we can log structured messages! 
# logger.info("STRUCTLOG User logged in", user_id="1234", ip="192.0.2.0")


ray.init() 

# @app.route('/')
# def index() -> JSON:
#   """_summary_

#   Args:
#       test (int, optional): _description_. Defaults to 1.

#   Returns:
#       JSON: _description_
#   """
#   return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})


@app.route('/coursera', methods=['GET'])
def coursera() -> JSON:
  try:
    course_name: str = request.args.get('course_name')  # type: ignore
    coursera_course_name: str = request.args.get('coursera_course_name')  # type: ignore
  except Exception as e:
    print(f"No course name provided: {e}")

  ingester = Ingest()
  results = ingester.ingest_coursera(coursera_course_name, course_name)  # type: ignore
  response = jsonify(results)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/github', methods=['GET'])
def github() -> JSON:
  try:
    course_name: str = request.args.get('course_name')  # type: ignore
    github_url: str = request.args.get('github_url')  # type: ignore
  except Exception as e:
    print(f"No course name provided: {e}")

  print("In /github")
  ingester = Ingest()
  results = ingester.ingest_github(github_url, course_name)
  response = jsonify(results)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/delete-entire-course', methods=['GET'])
def delete_entire_course():
  try:
    course_name: str = request.args.get('course_name')  # type: ignore
    # coursera_course_name: str = request.args.get('coursera_course_name') # type: ignore
  except Exception as e:
    print(f"No course name provided: {e}")

  ingester = Ingest()
  results = ingester.delete_entire_course(course_name)  # type: ignore
  response = jsonify(results)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/getTopContexts', methods=['GET'])
def getTopContexts():
  """Get most relevant contexts for a given search query.
  
  Return value

  ## GET arguments
  course name (optional) str
      A json response with TBD fields.
  search_query
  top_n
  
  Returns
  -------
  JSON
      A json response with TBD fields.
  Metadata fileds
  * pagenumber_or_timestamp
  * readable_filename
  * s3_pdf_path
  
  Example: 
  [
    {
      'readable_filename': 'Lumetta_notes', 
      'pagenumber_or_timestamp': 'pg. 19', 
      's3_pdf_path': '/courses/<course>/Lumetta_notes.pdf', 
      'text': 'In FSM, we do this...'
    }, 
  ]

  Raises
  ------
  Exception
      Testing how exceptions are handled.
  """
  # todo: best way to handle optional arguments?
  try:
    course_name: str = request.args.get('course_name')
    search_query: str = request.args.get('search_query')
    token_limit: int = request.args.get('token_limit')
  except Exception as e:
    print("No course name provided.")

  if search_query is None:
    return jsonify({"error": "No parameter `search_query` provided. It is undefined."})
  if token_limit is None:
    token_limit = 3_000
  else:
    token_limit = int(token_limit)

  ingester = Ingest()
  found_documents = ingester.getTopContexts(search_query, course_name, token_limit)

  response = jsonify(found_documents)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/get_stuffed_prompt', methods=['GET'])
def get_stuffed_prompt():
  """Get most relevant contexts for a given search query.
  
  ## GET arguments
  course name (optional) str
      A json response with TBD fields.
  search_query
  top_n
  
  Returns
  -------
    String
    
  """
  # todo: best way to handle optional arguments?
  try:
    course_name: str = request.args.get('course_name')
    search_query: str = request.args.get('search_query')
    token_limit: int = request.args.get('token_limit')
  except Exception as e:
    print("No course name provided.")

  print("In /getTopContexts: ", search_query)
  if search_query is None:
    return jsonify({"error": "No parameter `search_query` provided. It is undefined."})
  if token_limit is None:
    token_limit = 3_000
  else:
    token_limit = int(token_limit)

  ingester = Ingest()
  prompt = ingester.get_stuffed_prompt(search_query, course_name, token_limit)

  response = jsonify(prompt)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/ingest', methods=['GET'])
def ingest():
  """Recursively ingests anything from S3 filepath and below. 
  Pass a s3_paths filepath (not URL) into our S3 bucket.
  
  Ingests all files, not just PDFs. 
  
  args:
    s3_paths: str | List[str]

  Returns:
      str: Success or Failure message. Failure message if any failures. TODO: email on failure.
  """

  print("In /ingest")

  ingester = Ingest()
  s3_paths: List[str] | str = request.args.get('s3_paths')
  course_name: List[str] | str = request.args.get('course_name')
  success_fail_dict = ingester.bulk_ingest(s3_paths, course_name)

  response = jsonify(success_fail_dict)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/getContextStuffedPrompt', methods=['GET'])
def getContextStuffedPrompt():
  """
  Get a stuffed prompt for a given user question and course name.
  Args : 
    search_query (str)
    course_name (str) : used for metadata filtering
  Returns : str
    a very long "stuffed prompt" with question + summaries of 20 most relevant documents.
  """
  print("In /getContextStuffedPrompt")

  ingester = Ingest()
  search_query: str = str(request.args.get('search_query'))  # type: ignore
  course_name: str = str(request.args.get('course_name'))  # type: ignore
  top_n: int = int(request.args.get('top_n'))  # type: ignore
  top_k_to_search: int = int(request.args.get('top_k_to_search'))  # type: ignore

  start_time = time.monotonic()
  stuffed_prompt = ingester.get_context_stuffed_prompt(search_query, course_name, top_n, top_k_to_search)
  print(f"⏰ Runtime of EXTREME prompt stuffing: {(time.monotonic() - start_time):.2f} seconds")
  response = jsonify({"prompt": stuffed_prompt})

  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/getAll', methods=['GET'])
def getAll():
  """Get all course materials based on the course_name
  """

  print("In /getAll")

  ingester = Ingest()
  course_name: List[str] | str = request.args.get('course_name')
  distinct_dicts = ingester.getAll(course_name)
  response = jsonify({"all_s3_paths": distinct_dicts})

  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


#Write api to delete s3 files for a course
@app.route('/delete', methods=['DELETE'])
def delete():
  """Delete all course materials based on the course_name
    """

  print("In /delete")

  ingester = Ingest()
  course_name: List[str] | str = request.args.get('course_name')
  s3_path: str = request.args.get('s3_path')
  success_or_failure = ingester.delete_data(s3_path, course_name)
  response = jsonify({"outcome": success_or_failure})

  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/log', methods=['GET'])
def log():
  """
  todo
  """

  print("In /log")

  ingester = Ingest()
  # course_name: List[str] | str = request.args.get('course_name')
  success_or_failure = ingester.log_to_arize('course_name', 'test', 'completion')
  response = jsonify({"outcome": success_or_failure})

  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/web-scrape', methods=['GET'])
def scrape():
  url: str = request.args.get('url')
  max_urls: int = request.args.get('max_urls')
  max_depth: int = request.args.get('max_depth')
  timeout: int = request.args.get('timeout')
  course_name: str = request.args.get('course_name')
  base_url_bool: str = request.args.get('base_url_on')

  # print all input params
  print(f"Web scrape!")
  print(f"Url: {url}")
  print(f"Max Urls: {max_urls}")
  print(f"Max Depth: {max_depth}")
  print(f"Timeout in Seconds ⏰: {timeout}")

  success_fail_dict = main_crawler(url, course_name, max_urls, max_depth, timeout, base_url_bool)

  response = jsonify(success_fail_dict)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


@app.route('/mit-download', methods=['GET'])
def mit_download_course():
  url: str = request.args.get('url')
  course_name: str = request.args.get('course_name')
  local_dir: str = request.args.get('local_dir')

  success_fail = mit_course_download(url, course_name, local_dir)

  response = jsonify(success_fail)
  response.headers.add('Access-Control-Allow-Origin', '*')
  return response


# TODO: add a way to delete items from course based on base_url
from ai_ta_backend.agents import github_webhook_handlers


@app.route('/', methods=['POST']) # RUN: $ smee -u https://smee.io/nRnJDGnCbWYUaSGg --port 8000
# @app.route('/api/webhook', methods=['POST']) # https://flask-ai-ta-backend-pr-34.up.railway.app/api/webhook
def webhook():
  """
  IN PROGRESS: Github App Webhooks (for lil-jr-dev)
  Wehbook URL to use on my github app (if this route is `/api/webhook`): https://flask-ai-ta-backend-pr-34.up.railway.app/api/webhook

  DOCS: 
  API reference for Webhook objects: https://docs.github.com/en/webhooks-and-events/webhooks/webhook-events-and-payloads#issue_comment
  WEBHOOK explainer: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/using-webhooks-with-github-apps
  """

  payload = request.json
  # print(f"{payload}\n","-"*50, "\n")
  if not payload:
    raise ValueError(f"Missing the body of the webhook response. Response is {payload}")

  # API reference for webhook endpoints https://docs.github.com/en/webhooks-and-events/webhooks/webhook-events-and-payloads#issue_comment
  if payload.get('action') == 'opened' and payload.get('pull_request'):
    github_webhook_handlers.handle_pull_request_opened(payload)
  elif payload.get('action') in ['opened', 'edited'] and payload.get('issue'):
    github_webhook_handlers.handle_issue_opened(payload)
  elif payload.get('action') in ['created', 'edited'] and payload.get('comment'):
    github_webhook_handlers.handle_comment_opened(payload)

  return '', 200


if __name__ == '__main__':
  app.run(debug=True, port=os.getenv("PORT", default=8000))
