from github import Github, GithubException
from gitlab import Gitlab
from abc import ABC, abstractmethod
from fastapi import HTTPException

class VersionControlSystem(ABC):
    def __init__(self, repo_url, branch, user_data=None):
        print("Initializing VersionControlSystem...")
        self.repo_url = repo_url
        self.branch = branch
        self.user_data = user_data
        print(f"Initialized with Repo URL: {repo_url}, Branch: {branch}, User Data: {self.user_data}")

    def parse_url(self):
        print("Starting URL parsing...")
        parts = self.repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo = parts[-1].rstrip('/')
        ignore_segments = ['tree', 'blob', 'wiki', 'pull', 'issues', 'actions', 'projects', 'discussions', 'settings']
        index = None
        for segment in ignore_segments:
            if segment in parts:
                index = parts.index(segment)
                break
        if index is not None:
            branch = parts[index + 1]
            file_path = '/'.join(parts[index + 2:])
        else:
            branch = self.branch
            file_path = None
            if branch is None:
                print(f"Warning: Branch not found in URL and no branch provided during initialization for URL: {self.repo_url}")
        print(f"Parsed URL {self.repo_url} -> Owner: {owner}, Repo: {repo}, Branch: {branch}, File Path: {file_path}")
        return owner, repo, branch, file_path

    def can_access_private_repo(self, user_data):
        print("Starting private repo access check...")
        print(f"Checking subscription: {self.user_data}")
        if not self.user_data or "plan_id" not in self.user_data:
            print("Access denied due to missing plan_id.")
            raise ValueError("You need a plan in order to access your private data.")
        print("[STATUS] Credentials Verified")
        return True

    @abstractmethod
    async def list_files(self):
        print("Abstract method list_files called.")
        pass

    @abstractmethod
    async def get_file_content(self, path):
        print("Abstract method get_file_content called.")
        pass

    @abstractmethod
    async def list_branches(self):
        print("Abstract method list_branches called.")
        pass

class GitHub(VersionControlSystem):
    def __init__(self, repo_url, branch=None, user_data=None):
        print("Initializing GitHub...")
        super().__init__(repo_url, branch, user_data)
        self.github_client = Github(self.user_data.get('github_token')) if self.user_data and self.user_data.get('github_token') else Github()
        print(f"GitHub initialized with Repo URL: {repo_url}, Branch: {branch}, User Data: {self.user_data}")

    def is_private(self):
        print("Checking repository visibility on GitHub...")
        owner, repo, _, _ = self.parse_url()
        try:
            repo = self.github_client.get_repo(f'{owner}/{repo}')
            print(f"Repo {repo.name} is {'private' if repo.private else 'public'}")
            return repo.private
        except GithubException as e:
            if e.status == 404:
                print("Repository not found or access denied on GitHub.")
                raise HTTPException(status_code=404, detail="Repository not found or access denied.")
            raise e

    async def list_files(self):
      print("Starting file listing on GitHub...")
      if self.is_private() and not self.can_access_private_repo(self.user_data):
          return "You need a plan in order to access your private data."
      owner, repo, branch, _ = self.parse_url()
      print(f"Listing files from GitHub for Owner: {owner}, Repo: {repo}, Branch: {branch}")
      try:
          repo_obj = self.github_client.get_repo(f'{owner}/{repo}')
          branch_to_use = branch if branch is not None else repo_obj.default_branch
          print(f"Using branch: {branch_to_use}")
          tree = repo_obj.get_git_tree(branch_to_use, recursive=True).tree
          files = [element.path for element in tree]
          print(f"Files found: {files}")
          return files
      except GithubException as e:
          print(f"Error while listing files on GitHub: {e}")
          raise e

    async def get_file_content(self, path):
        print("Fetching file content from GitHub...")
        if self.is_private() and not self.can_access_private_repo(self.user_data):
            return "You need a plan in order to access your private data."
        owner, repo, branch, _ = self.parse_url()
        print(f"Fetching file content from GitHub for Path: {path}, Branch: {branch}")
        try:
            repo_obj = self.github_client.get_repo(f'{owner}/{repo}')
            branch = self.branch if self.branch is not None else repo_obj.default_branch
            file_content = repo_obj.get_contents(path, ref=branch)
            content = file_content.decoded_content.decode()
            print(f"File content fetched: {content}")
            return content
        except GithubException as e:
            print(f"Error while fetching file content from GitHub: {e}")
            raise e

    async def list_branches(self):
        print("Listing branches on GitHub...")
        if self.is_private() and not self.can_access_private_repo(self.user_data):
            return "You need a plan in order to access your private data."
        owner, repo, _, _ = self.parse_url()
        print(f"Listing branches from GitHub for Owner: {owner}, Repo: {repo}")
        try:
            repo = self.github_client.get_repo(f'{owner}/{repo}')
            branches = repo.get_branches()
            branch_names = [branch.name for branch in branches]
            print(f"Branches found: {branch_names}")
            return branch_names
        except GithubException as e:
            print(f"Error while listing branches on GitHub: {e}")
            raise e

class GitLab(VersionControlSystem):
    def __init__(self, repo_url, branch=None, user_data=None):
        print("Initializing GitLab...")
        super().__init__(repo_url, branch, user_data)
        self.gitlab_client = Gitlab('https://gitlab.com', private_token=self.user_data.get('gitlab_token')) if self.user_data and self.user_data.get('gitlab_token') else Gitlab('https://gitlab.com')
        print(f"GitLab initialized with Repo URL: {repo_url}, Branch: {branch}, User Data: {self.user_data}")

    def is_private(self):
        print("Checking visibility on GitLab...")
        owner, name, _, _ = self.parse_url()
        project = self.gitlab_client.projects.get(f'{owner}/{name}')
        visibility = project.attributes.get("visibility")
        print(f"Visibility of the project on GitLab: {visibility}")
        return visibility == "private"
  
    async def list_files(self):
        print("Listing files on GitLab...")
        if self.is_private() and not self.can_access_private_repo(self.user_data):
            return "You need a plan in order to access your private data"
        owner, name, _, _ = self.parse_url()
        project = self.gitlab_client.projects.get(f'{owner}/{name}')
        items = project.repository_tree(ref=self.branch, recursive=True, all=True)
        files = [item['path'] for item in items]
        print(f"Files found on GitLab: {files}")
        return files

    async def get_file_content(self, path):
        print("Fetching file content from GitLab...")
        if self.is_private() and not self.can_access_private_repo(self.user_data):
            return []
        owner, name, branch, _ = self.parse_url()
        project = self.gitlab_client.projects.get(f'{owner}/{name}')
        branch = self.branch if self.branch is not None else project.default_branch
        file_content = project.files.get(file_path=path, ref=branch)
        file_content.decode()
        content = file_content.content
        print(f"File content fetched from GitLab: {content}")
        return content

    async def list_branches(self):
        print("Listing branches on GitLab...")
        owner, name, _, _ = self.parse_url()
        project = self.gitlab_client.projects.get(f'{owner}/{name}')
        branches = project.branches.list()
        branch_names = [branch.name for branch in branches]
        print(f"Branches found on GitLab: {branch_names}")
        return branch_names

def get_vcs(repo_url, branch=None, user_data=None):
    print("Determining Version Control System...")
    if 'github.com' in repo_url:
        print("Detected GitHub.")
        return GitHub(repo_url, branch, user_data)
    elif 'gitlab.com' in repo_url:
        print("Detected GitLab.")
        return GitLab(repo_url, branch, user_data)
    else:
        print("Error: Couldn't determine Hub/Lab Control")
        raise ValueError("Couldn't determine Hub/Lab Control")
