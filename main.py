import json
import time
import os
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
from supabase_py import create_client, Client
from starlette.responses import Response
from starlette.types import Receive, Send, Scope
from github_data_api import list_files, get_file_content, create_new_repo, list_branches, MessageHandler, log_event, delete_file
supabase_url = os.environ['SUPABASE_URL']
supabase_key = os.environ['SUPABASE_KEY']
supabase: Client = create_client(supabase_url, supabase_key)


class LoggingResponse(Response):

  async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
    start_time = time.time()

    async def logging_send(message: dict) -> None:
      if message.get("type") == "http.response.body":
        body = message.get("body").decode()
        event = {
          "Date": datetime.now().isoformat(),
          "Method": scope["method"],
          "Path": scope["path"],
          "Status": self.status_code,
          "Duration": time.time() - start_time,
          "Event": body,
          "Messages": message_handler.messages  # Add this line
        }
        log_event(supabase, event)
      await send(message)

    await super().__call__(scope, receive, logging_send)


app = FastAPI()

origins = ["https://chat.openai.com"]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.mount("/.well-known",
          StaticFiles(directory=".well-known"),
          name=".well-known")


class RepoData(BaseModel):
  repo_url: str
  branch: Optional[str] = 'main'


class FileData(BaseModel):
  repo_url: str
  path: str
  branch: Optional[str] = 'main'


class NewRepoData(BaseModel):
  name: str
  description: Optional[str] = ''
  private: Optional[bool] = False

class DeleteFileData(BaseModel):
  repo_url: str
  file_name: str
  commit_message: str
  branch: Optional[str] = 'main'

class ForkRepoData(BaseModel):
  repo_url: str

message_handler = MessageHandler()


@app.get("/")
def root():
  print_and_store("Root endpoint called")
  return LoggingResponse(content=json.dumps(
    {"message": "Spinning up Recombinant AI™"}),
                         media_type="application/json")


@app.get("/get_status_messages")
async def get_status_messages():
  return LoggingResponse(content=json.dumps(
    {"messages": message_handler.messages[-15:]}),
                         media_type="application/json")


@app.post("/get_repo_files")
async def get_repo_files(data: RepoData):
  print_and_store("get_repo_files endpoint called")
  parts = data.repo_url.split('/')
  owner = parts[-2]
  repo = parts[-1]
  files = [
    f async for f in list_files(message_handler, owner, repo, data.branch)
  ]
  return {"files": files}


@app.post("/get_file_content")
async def get_file_content_route(data: FileData):
  print_and_store("get_file_content endpoint called")
  parts = data.repo_url.split('/')
  owner = parts[-2]
  repo = parts[-1]
  content = get_file_content(message_handler, owner, repo, data.branch,
                             data.path)
  return LoggingResponse(content=json.dumps({"content": content}),
                         media_type="application/json")


@app.post("/list_branches")
async def list_branches_route(data: RepoData):
  print_and_store("list_branches endpoint called")
  parts = data.repo_url.split('/')
  owner = parts[-2]
  repo = parts[-1]
  branches = list_branches(message_handler, owner, repo)
  return LoggingResponse(content=json.dumps({"branches": branches}),
                         media_type="application/json")

@app.post("/create_new_repo")
def create_new_repo_route(data: NewRepoData):
  print_and_store("create_new_repo endpoint called")
  repo = create_new_repo(message_handler, data.name, data.description,
                         data.private)
  if repo is None:
    return LoggingResponse(content=json.dumps(
      {"error": "Failed to create repository"}),
                           media_type="application/json",
                           status_code=500)
  return LoggingResponse(content=json.dumps({"repo": repo.raw_data}),
                         media_type="application/json")


@app.post("/delete_file")
async def delete_file_route(data: DeleteFileData):
  print_and_store("delete_file endpoint called")
  parts = data.repo_url.split('/')
  owner = parts[-2]
  repo = parts[-1]
  delete_file(message_handler, owner, repo, data.file_name,
              data.commit_message, data.branch)
  return {"message": "File deleted successfully"}


@app.get("/RecombLogo.png")
async def plugin_logo():
  print_and_store("logo.png endpoint called")
  return FileResponse("RecombLogo.png")


def print_and_store(message):
  message_handler.print_and_store(message, supabase)


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
