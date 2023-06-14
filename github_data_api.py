import base64
import os
import requests
from github import Github, GithubException
from datetime import datetime
from supabase_py import Client, create_client
import aiohttp


my_secret = os.environ['GITHUB_TOKEN']
g = Github(my_secret)
supabase_url = os.environ['SUPABASE_URL']
supabase_key = os.environ['SUPABASE_KEY']
supabase: Client = create_client(supabase_url, supabase_key)


class MessageHandler:

  def __init__(self):
    self.messages = []

  def print_and_store(self, message, supabase: Client):
    print(message)
    self.messages.append(message)
    self.messages[:] = self.messages[-15:]
    self.log_to_supabase(message, supabase)

  def log_to_supabase(self, message, supabase: Client):
    supabase.table('Events').insert([
      {
        'timestamp': datetime.now(),
        'event': message,
      },
    ])


def print_and_store(message_handler, message):
  message_handler.print_and_store(message, supabase)


def log_event(supabase: Client, event: dict):
  supabase.table('Events').insert([event]).execute()

async def list_files(message_handler,
               owner,
               repo,
               branch=None,
               path='',
               depth=0,
               max_depth=10,
               visited=None):
  # If the depth exceeds the maximum depth, return.
  if depth > max_depth:
    return

  # Initialize the visited set if it's None.
  if visited is None:
    visited = set()

  # If we've visited this directory before, return to avoid an infinite loop.
  if path in visited:
    return

  # Add the current directory to the visited set.
  visited.add(path)

  if branch is None:
    branches = ['main', 'master']
  else:
    branches = [branch]

  for branch in branches:
    try:
      print_and_store(
        message_handler,
        f"Fetching files for repo: {owner}/{repo}, path: {path}, branch: {branch}"
      )
      url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
      headers = {'Authorization': f'token {my_secret}'}
      async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
          print_and_store(message_handler,
                          f"GitHub API response: {response.status}")

          if response.status == 200:
            files = await response.json()
            for file in files:
              if file['type'] == 'dir':
                print_and_store(message_handler,
                                f"Found directory: {file['name']}")
                # If the directory is named 'node_modules', yield it and skip its contents.
                if file['name'] == 'node_modules':
                  yield {file['name']: 'Skipped'}
                  continue
                # Yield the directory and recursively list its files.
                async for f in list_files(message_handler, owner, repo, branch, file['path'],
                             depth + 1, max_depth, visited):
                  yield {file['name']: f}
              else:
                print_and_store(message_handler, f"Found file: {file['name']}")
                # Yield the file.
                yield file['name']
          else:
            print_and_store(message_handler,
                            "Failed to fetch files from GitHub API")
            continue
    except GithubException as e:
      print_and_store(message_handler, f"GitHub API exception: {e}")
      continue




def get_file_content(message_handler, owner, repo, branch=None, path=''):
  if branch is None:
    branches = ['main', 'master']
  else:
    branches = [branch]
  for branch in branches:
    try:
      print_and_store(
        message_handler,
        f"Fetching file content for repo: {owner}/{repo}, path: {path}, branch: {branch}"
      )
      print_and_store(message_handler, "Step 1: Getting repo and tree...")
      repo = g.get_repo(f"{owner}/{repo}")
      tree = repo.get_git_tree(branch, recursive=True)
      print_and_store(message_handler, "Step 2: Searching for file in tree...")
      for element in tree.tree:
        if element.path == path:
          print_and_store(message_handler, "Step 3: Fetching file content...")
          blob = repo.get_git_blob(element.sha)
          content = base64.b64decode(blob.content).decode('utf-8')
          print_and_store(message_handler, "File content fetched successfully")
          return content
      print_and_store(message_handler, "File not found in GitHub API")
      continue
    except GithubException:
      continue
  return None

def create_new_repo(message_handler, name, description='', private=False):
    try:
        print_and_store(message_handler, f"Creating new repo: {name}")
        user = g.get_user()
        repo = user.create_repo(name, description=description, private=private)
        print_and_store(message_handler, 
 "Repository created successfully")
        return repo
    except GithubException as e:
        print_and_store(message_handler, f"Failed to create repository in GitHub API: {e}")
        return None
    except Exception as e:
        print_and_store(message_handler, f"An unexpected error occurred: {e}")
        return None

      
def delete_file(repo, file_name, commit_message):
    try :
        contents = repo.get_contents(file_name)
        repo.delete_file(contents.path, commit_message, contents.sha)
        print(f"File {file_name} successfully deleted from repository {repo.name}")
    except GithubException as e:
        print(f"Failed to create file in GitHub API: {e}")


def list_branches(message_handler, owner, repo):
  print_and_store(message_handler,
                  f"Fetching branches for repo: {owner}/{repo}")
  url = f"https://api.github.com/repos/{owner}/{repo}/branches"
  headers = {'Authorization': f'token {my_secret}'}
  response = requests.get(url, headers=headers)
  print_and_store(message_handler,
                  f"GitHub API response: {response.status_code}")
  print_and_store(message_handler, response.text)
  if response.status_code == 200:
    branches = response.json()
    branch_list = [branch['name'] for branch in branches]
    return branch_list
  else:
    print_and_store(message_handler,
                    "Failed to fetch branches from GitHub API")
    return []



