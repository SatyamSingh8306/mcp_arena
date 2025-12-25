from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
from atlassian.bitbucket import Bitbucket
from atlassian.bitbucket.cloud import Cloud
import json
import base64
from pathlib import Path
from enum import Enum
from mcp_arena.mcp.server import BaseMCPServer

class PullRequestState(Enum):
    """Pull request state enumeration."""
    OPEN = "OPEN"
    MERGED = "MERGED"
    DECLINED = "DECLINED"
    SUPERSEDED = "SUPERSEDED"

class IssueState(Enum):
    """Issue state enumeration."""
    NEW = "new"
    OPEN = "open"
    RESOLVED = "resolved"
    ON_HOLD = "on hold"
    INVALID = "invalid"
    DUPLICATE = "duplicate"
    WONT_FIX = "wontfix"
    CLOSED = "closed"

@dataclass
class WorkspaceInfo:
    """Information about a Bitbucket workspace."""
    uuid: str
    name: str
    slug: str
    is_private: bool
    created_on: str
    updated_on: str
    
@dataclass
class RepositoryInfo:
    """Information about a Bitbucket repository."""
    uuid: str
    name: str
    full_name: str
    description: str
    website: Optional[str]
    language: str
    created_on: str
    updated_on: str
    size: int
    has_issues: bool
    has_wiki: bool
    fork_policy: str
    project: Dict[str, Any]
    mainbranch: Dict[str, Any]
    links: Dict[str, Any]
    
@dataclass
class PullRequestInfo:
    """Information about a pull request."""
    id: int
    title: str
    description: str
    state: str
    created_on: str
    updated_on: str
    source_branch: str
    destination_branch: str
    author: Dict[str, Any]
    reviewers: List[Dict[str, Any]]
    participants: List[Dict[str, Any]]
    comment_count: int
    task_count: int
    close_source_branch: bool
    merge_commit: Optional[Dict[str, Any]]
    links: Dict[str, Any]
    
@dataclass
class CommitInfo:
    """Information about a commit."""
    hash: str
    message: str
    author: Dict[str, Any]
    parents: List[Dict[str, Any]]
    date: str
    summary: Dict[str, Any]
    
@dataclass
class BranchInfo:
    """Information about a branch."""
    name: str
    target: Dict[str, Any]
    default_merge_strategy: str
    merge_strategies: List[str]
    links: Dict[str, Any]
    
@dataclass
class IssueInfo:
    """Information about an issue."""
    id: int
    title: str
    content: Dict[str, Any]
    state: str
    kind: str
    priority: str
    votes: int
    watches: int
    created_on: str
    updated_on: str
    reporter: Dict[str, Any]
    assignee: Optional[Dict[str, Any]]
    milestone: Optional[Dict[str, Any]]
    component: Optional[Dict[str, Any]]
    version: Optional[Dict[str, Any]]
    
@dataclass
class PipelineInfo:
    """Information about a pipeline."""
    uuid: str
    build_number: int
    name: str
    state: Dict[str, Any]
    created_on: str
    completed_on: Optional[str]
    target: Dict[str, Any]
    trigger: Dict[str, Any]
    duration_in_seconds: Optional[int]
    
@dataclass
class FileInfo:
    """Information about a file."""
    path: str
    type: str
    size: int
    commit_hash: str
    mime_type: Optional[str]
    links: Dict[str, Any]

class BitbucketMCPServer(BaseMCPServer):
    """Bitbucket MCP Server for Bitbucket Cloud operations."""
    
    def __init__(
        self,
        url: str = "https://api.bitbucket.org",
        username: Optional[str] = None,
        app_password: Optional[str] = None,
        oauth_key: Optional[str] = None,
        oauth_secret: Optional[str] = None,
        cloud: bool = True,
        timeout: int = 60,
        host: str = "127.0.0.1",
        port: int = 8005,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Bitbucket MCP Server.
        
        Args:
            url: Bitbucket API URL
            username: Bitbucket username
            app_password: Bitbucket app password
            oauth_key: OAuth consumer key
            oauth_secret: OAuth consumer secret
            cloud: Use Bitbucket Cloud (True) or Server (False)
            timeout: Request timeout in seconds
            host: Host to run MCP server on
            port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        try:
            if cloud:
                # Bitbucket Cloud
                if oauth_key and oauth_secret:
                    self.bitbucket_client = Cloud(
                        url=url,
                        oauth={'key': oauth_key, 'secret': oauth_secret}
                    )
                elif username and app_password:
                    self.bitbucket_client = Cloud(
                        url=url,
                        username=username,
                        password=app_password
                    )
                else:
                    # Try environment variables
                    import os
                    username = os.environ.get('BITBUCKET_USERNAME')
                    app_password = os.environ.get('BITBUCKET_APP_PASSWORD')
                    if username and app_password:
                        self.bitbucket_client = Cloud(
                            url=url,
                            username=username,
                            password=app_password
                        )
                    else:
                        raise ValueError("Authentication credentials required")
            else:
                # Bitbucket Server (Data Center)
                if username and app_password:
                    self.bitbucket_client = Bitbucket(
                        url=url,
                        username=username,
                        password=app_password,
                        cloud=cloud
                    )
                else:
                    raise ValueError("Username and app password required for Bitbucket Server")
            
            # Test connection
            self.bitbucket_client.get_user()
            self.connected = True
            self.is_cloud = cloud
            
        except Exception as e:
            self.connected = False
            self.bitbucket_client = None
            if debug:
                print(f"Bitbucket connection failed: {e}")
        
        # Initialize base class
        super().__init__(
            name="Bitbucket MCP Server",
            description="MCP server for Bitbucket Cloud operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _check_connection(self) -> bool:
        """Check Bitbucket connection."""
        if not self.connected or not self.bitbucket_client:
            return False
        try:
            self.bitbucket_client.get_user()
            return True
        except Exception:
            self.connected = False
            return False
    
    def _parse_repository(self, repo) -> RepositoryInfo:
        """Parse Bitbucket repository object."""
        return RepositoryInfo(
            uuid=repo.get('uuid', ''),
            name=repo.get('name', ''),
            full_name=repo.get('full_name', ''),
            description=repo.get('description', ''),
            website=repo.get('website'),
            language=repo.get('language', ''),
            created_on=repo.get('created_on', ''),
            updated_on=repo.get('updated_on', ''),
            size=repo.get('size', 0),
            has_issues=repo.get('has_issues', False),
            has_wiki=repo.get('has_wiki', False),
            fork_policy=repo.get('fork_policy', 'allow_forks'),
            project=repo.get('project', {}),
            mainbranch=repo.get('mainbranch', {}),
            links=repo.get('links', {})
        )
    
    def _parse_pull_request(self, pr) -> PullRequestInfo:
        """Parse Bitbucket pull request object."""
        return PullRequestInfo(
            id=pr.get('id', 0),
            title=pr.get('title', ''),
            description=pr.get('description', {}).get('raw', '') if isinstance(pr.get('description'), dict) else pr.get('description', ''),
            state=pr.get('state', 'OPEN'),
            created_on=pr.get('created_on', ''),
            updated_on=pr.get('updated_on', ''),
            source_branch=pr.get('source', {}).get('branch', {}).get('name', ''),
            destination_branch=pr.get('destination', {}).get('branch', {}).get('name', ''),
            author=pr.get('author', {}),
            reviewers=pr.get('reviewers', []),
            participants=pr.get('participants', []),
            comment_count=pr.get('comment_count', 0),
            task_count=pr.get('task_count', 0),
            close_source_branch=pr.get('close_source_branch', False),
            merge_commit=pr.get('merge_commit'),
            links=pr.get('links', {})
        )
    
    def _register_tools(self) -> None:
        """Register all Bitbucket-related tools."""
        self._register_workspace_tools()
        self._register_repository_tools()
        self._register_pull_request_tools()
        self._register_commit_tools()
        self._register_branch_tools()
        self._register_pipeline_tools()
    
    def _register_workspace_tools(self):
        """Register workspace tools."""
        
        @self.mcp_server.tool()
        def list_workspaces() -> Dict[str, Any]:
            """List Bitbucket workspaces."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    workspaces = self.bitbucket_client.workspaces.get()
                else:
                    # Bitbucket Server
                    workspaces = []
                
                workspace_list = []
                for workspace in workspaces:
                    workspace_info = WorkspaceInfo(
                        uuid=workspace.get('uuid', ''),
                        name=workspace.get('name', ''),
                        slug=workspace.get('slug', ''),
                        is_private=workspace.get('is_private', True),
                        created_on=workspace.get('created_on', ''),
                        updated_on=workspace.get('updated_on', '')
                    )
                    workspace_list.append(asdict(workspace_info))
                
                return {
                    "count": len(workspace_list),
                    "workspaces": workspace_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_workspace(workspace_slug: str) -> Dict[str, Any]:
            """Get information about a specific workspace."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    workspace = self.bitbucket_client.workspaces.get(workspace_slug)
                else:
                    return {"error": "Not supported for Bitbucket Server"}
                
                workspace_info = WorkspaceInfo(
                    uuid=workspace.get('uuid', ''),
                    name=workspace.get('name', ''),
                    slug=workspace.get('slug', ''),
                    is_private=workspace.get('is_private', True),
                    created_on=workspace.get('created_on', ''),
                    updated_on=workspace.get('updated_on', '')
                )
                
                return {
                    "workspace": asdict(workspace_info)
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_repository_tools(self):
        """Register repository tools."""
        
        @self.mcp_server.tool()
        def list_repositories(
            workspace_slug: Optional[str] = None,
            search: Optional[str] = None
        ) -> Dict[str, Any]:
            """List Bitbucket repositories.
            
            Args:
                workspace_slug: Workspace slug (required for Bitbucket Cloud)
                search: Search repositories by name
            """
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    if not workspace_slug:
                        return {"error": "workspace_slug is required for Bitbucket Cloud"}
                    
                    repos = self.bitbucket_client.repositories.list(workspace_slug)
                else:
                    # Bitbucket Server
                    repos = self.bitbucket_client.get_repos()
                
                repository_list = []
                for repo in repos:
                    try:
                        repo_data = repo if isinstance(repo, dict) else repo.__dict__
                        repo_info = self._parse_repository(repo_data)
                        
                        # Apply search filter
                        if search and search.lower() not in repo_info.name.lower():
                            continue
                        
                        repository_list.append(asdict(repo_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing repository: {e}")
                        continue
                
                return {
                    "workspace": workspace_slug or "all",
                    "count": len(repository_list),
                    "repositories": repository_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_repository(
            workspace_slug: str,
            repository_slug: str
        ) -> Dict[str, Any]:
            """Get detailed information about a repository."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                else:
                    repo = self.bitbucket_client.get_repo(repository_slug)
                
                repo_info = self._parse_repository(repo)
                
                return {
                    "repository": asdict(repo_info)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_repository(
            workspace_slug: str,
            name: str,
            description: Optional[str] = None,
            is_private: bool = True,
            fork_policy: str = "allow_forks",
            project_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new repository.
            
            Args:
                workspace_slug: Workspace slug
                name: Repository name
                description: Repository description
                is_private: Make repository private
                fork_policy: Fork policy (allow_forks, no_public_forks, no_forks)
                project_key: Project key to associate with
            """
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo_data = {
                        "name": name,
                        "is_private": is_private,
                        "fork_policy": fork_policy
                    }
                    
                    if description:
                        repo_data["description"] = description
                    if project_key:
                        repo_data["project"] = {"key": project_key}
                    
                    repo = self.bitbucket_client.repositories.create(
                        workspace_slug, **repo_data
                    )
                else:
                    return {"error": "Repository creation not implemented for Bitbucket Server"}
                
                repo_info = self._parse_repository(repo)
                
                return {
                    "success": True,
                    "repository": asdict(repo_info),
                    "message": f"Repository '{name}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_pull_request_tools(self):
        """Register pull request tools."""
        
        @self.mcp_server.tool()
        def list_pull_requests(
            workspace_slug: str,
            repository_slug: str,
            state: str = "OPEN",
            author: Optional[str] = None
        ) -> Dict[str, Any]:
            """List pull requests for a repository.
            
            Args:
                workspace_slug: Workspace slug
                repository_slug: Repository slug
                state: Pull request state (OPEN, MERGED, DECLINED, SUPERSEDED)
                author: Filter by author username
            """
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    prs = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    ).pullrequests.each(state=state)
                else:
                    return {"error": "Not implemented for Bitbucket Server"}
                
                pr_list = []
                for pr in prs:
                    pr_info = self._parse_pull_request(pr)
                    
                    # Apply author filter
                    if author and author.lower() not in pr_info.author.get('display_name', '').lower():
                        continue
                    
                    pr_list.append(asdict(pr_info))
                
                return {
                    "repository": f"{workspace_slug}/{repository_slug}",
                    "count": len(pr_list),
                    "pull_requests": pr_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_pull_request(
            workspace_slug: str,
            repository_slug: str,
            title: str,
            source_branch: str,
            destination_branch: str,
            description: Optional[str] = None,
            reviewers: Optional[List[str]] = None,
            close_source_branch: bool = True
        ) -> Dict[str, Any]:
            """Create a new pull request.
            
            Args:
                workspace_slug: Workspace slug
                repository_slug: Repository slug
                title: Pull request title
                source_branch: Source branch name
                destination_branch: Destination branch name
                description: Pull request description
                reviewers: List of reviewer usernames
                close_source_branch: Close source branch after merge
            """
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    pr_data = {
                        "title": title,
                        "source": {"branch": {"name": source_branch}},
                        "destination": {"branch": {"name": destination_branch}},
                        "close_source_branch": close_source_branch
                    }
                    
                    if description:
                        pr_data["description"] = {"raw": description}
                    if reviewers:
                        pr_data["reviewers"] = [{"username": r} for r in reviewers]
                    
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    pr = repo.pullrequests.create(**pr_data)
                else:
                    return {"error": "Not implemented for Bitbucket Server"}
                
                pr_info = self._parse_pull_request(pr)
                
                return {
                    "success": True,
                    "pull_request": asdict(pr_info),
                    "message": f"Pull request '{title}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def merge_pull_request(
            workspace_slug: str,
            repository_slug: str,
            pull_request_id: int,
            merge_strategy: str = "merge_commit",
            message: Optional[str] = None,
            close_source_branch: bool = True
        ) -> Dict[str, Any]:
            """Merge a pull request."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    pr = repo.pullrequests.get(pull_request_id)
                    
                    merge_data = {
                        "type": merge_strategy,
                        "close_source_branch": close_source_branch
                    }
                    
                    if message:
                        merge_data["message"] = message
                    
                    result = pr.merge(**merge_data)
                    
                    return {
                        "success": True,
                        "pull_request_id": pull_request_id,
                        "merged": result.get('merged', False),
                        "message": f"Pull request #{pull_request_id} merged successfully"
                    }
                else:
                    return {"error": "Not implemented for Bitbucket Server"}
            except Exception as e:
                return {"error": str(e)}
    
    def _register_commit_tools(self):
        """Register commit tools."""
        
        @self.mcp_server.tool()
        def list_commits(
            workspace_slug: str,
            repository_slug: str,
            branch: str = "main",
            limit: int = 50
        ) -> Dict[str, Any]:
            """List commits for a repository.
            
            Args:
                workspace_slug: Workspace slug
                repository_slug: Repository slug
                branch: Branch name
                limit: Maximum number of commits to return
            """
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    commits = repo.commits.list(branch, limit=limit)
                else:
                    return {"error": "Not implemented for Bitbucket Server"}
                
                commit_list = []
                for commit in commits:
                    commit_info = CommitInfo(
                        hash=commit.get('hash', ''),
                        message=commit.get('message', ''),
                        author=commit.get('author', {}),
                        parents=commit.get('parents', []),
                        date=commit.get('date', ''),
                        summary=commit.get('summary', {})
                    )
                    commit_list.append(asdict(commit_info))
                
                return {
                    "repository": f"{workspace_slug}/{repository_slug}",
                    "branch": branch,
                    "count": len(commit_list),
                    "commits": commit_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_commit(
            workspace_slug: str,
            repository_slug: str,
            commit_hash: str
        ) -> Dict[str, Any]:
            """Get detailed information about a specific commit."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    commit = repo.commits.get(commit_hash)
                else:
                    return {"error": "Not implemented for Bitbucket Server"}
                
                commit_info = CommitInfo(
                    hash=commit.get('hash', ''),
                    message=commit.get('message', ''),
                    author=commit.get('author', {}),
                    parents=commit.get('parents', []),
                    date=commit.get('date', ''),
                    summary=commit.get('summary', {})
                )
                
                return {
                    "commit": asdict(commit_info)
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_branch_tools(self):
        """Register branch tools."""
        
        @self.mcp_server.tool()
        def list_branches(
            workspace_slug: str,
            repository_slug: str,
            search: Optional[str] = None
        ) -> Dict[str, Any]:
            """List branches for a repository."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    branches = repo.branches.each()
                else:
                    return {"error": "Not implemented for Bitbucket Server"}
                
                branch_list = []
                for branch in branches:
                    branch_info = BranchInfo(
                        name=branch.get('name', ''),
                        target=branch.get('target', {}),
                        default_merge_strategy=branch.get('default_merge_strategy', ''),
                        merge_strategies=branch.get('merge_strategies', []),
                        links=branch.get('links', {})
                    )
                    
                    # Apply search filter
                    if search and search.lower() not in branch_info.name.lower():
                        continue
                    
                    branch_list.append(asdict(branch_info))
                
                return {
                    "repository": f"{workspace_slug}/{repository_slug}",
                    "count": len(branch_list),
                    "branches": branch_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_branch(
            workspace_slug: str,
            repository_slug: str,
            branch_name: str,
            from_branch: str = "main"
        ) -> Dict[str, Any]:
            """Create a new branch.
            
            Args:
                workspace_slug: Workspace slug
                repository_slug: Repository slug
                branch_name: New branch name
                from_branch: Source branch name
            """
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    
                    # Get latest commit from source branch
                    commits = repo.commits.list(from_branch, limit=1)
                    if not commits:
                        return {"error": f"Source branch '{from_branch}' not found"}
                    
                    latest_commit = next(commits)
                    
                    # Create branch
                    branch_data = {
                        "name": branch_name,
                        "target": {"hash": latest_commit.get('hash')}
                    }
                    
                    branch = repo.branches.create(**branch_data)
                    
                    return {
                        "success": True,
                        "branch": branch_name,
                        "from_branch": from_branch,
                        "commit_hash": latest_commit.get('hash'),
                        "message": f"Branch '{branch_name}' created from '{from_branch}'"
                    }
                else:
                    return {"error": "Not implemented for Bitbucket Server"}
            except Exception as e:
                return {"error": str(e)}
    
    def _register_pipeline_tools(self):
        """Register pipeline tools."""
        
        @self.mcp_server.tool()
        def list_pipelines(
            workspace_slug: str,
            repository_slug: str,
            status: Optional[str] = None
        ) -> Dict[str, Any]:
            """List CI/CD pipelines for a repository."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    
                    pipelines = repo.pipelines.list()
                else:
                    return {"error": "Pipelines not supported for Bitbucket Server"}
                
                pipeline_list = []
                for pipeline in pipelines:
                    pipeline_info = PipelineInfo(
                        uuid=pipeline.get('uuid', ''),
                        build_number=pipeline.get('build_number', 0),
                        name=pipeline.get('name', ''),
                        state=pipeline.get('state', {}),
                        created_on=pipeline.get('created_on', ''),
                        completed_on=pipeline.get('completed_on'),
                        target=pipeline.get('target', {}),
                        trigger=pipeline.get('trigger', {}),
                        duration_in_seconds=pipeline.get('duration_in_seconds')
                    )
                    
                    # Apply status filter
                    if status and status.lower() not in pipeline_info.state.get('name', '').lower():
                        continue
                    
                    pipeline_list.append(asdict(pipeline_info))
                
                return {
                    "repository": f"{workspace_slug}/{repository_slug}",
                    "count": len(pipeline_list),
                    "pipelines": pipeline_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def trigger_pipeline(
            workspace_slug: str,
            repository_slug: str,
            branch: str = "main",
            variables: Optional[Dict[str, str]] = None
        ) -> Dict[str, Any]:
            """Trigger a new pipeline."""
            if not self._check_connection():
                return {"error": "Bitbucket connection not available"}
            
            try:
                if self.is_cloud:
                    repo = self.bitbucket_client.repositories.get(
                        workspace_slug, repository_slug
                    )
                    
                    pipeline_data = {
                        "target": {
                            "ref_type": "branch",
                            "type": "pipeline_ref_target",
                            "ref_name": branch
                        }
                    }
                    
                    if variables:
                        pipeline_data["variables"] = [
                            {"key": k, "value": v} for k, v in variables.items()
                        ]
                    
                    pipeline = repo.pipelines.trigger(**pipeline_data)
                    
                    return {
                        "success": True,
                        "pipeline_uuid": pipeline.get('uuid'),
                        "branch": branch,
                        "message": f"Pipeline triggered for branch '{branch}'"
                    }
                else:
                    return {"error": "Pipelines not supported for Bitbucket Server"}
            except Exception as e:
                return {"error": str(e)}


# CLI interface
if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Bitbucket MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="MCP server host")
    parser.add_argument("--port", type=int, default=8005, help="MCP server port")
    parser.add_argument("--bitbucket-url", default="https://api.bitbucket.org", 
                       help="Bitbucket API URL")
    parser.add_argument("--username", help="Bitbucket username")
    parser.add_argument("--app-password", help="Bitbucket app password")
    parser.add_argument("--oauth-key", help="OAuth consumer key")
    parser.add_argument("--oauth-secret", help="OAuth consumer secret")
    parser.add_argument("--server", action="store_true", 
                       help="Use Bitbucket Server (default: Cloud)")
    parser.add_argument("--transport", default="stdio", 
                       choices=['stdio', 'sse', 'streamable-http'],
                       help="Transport type")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Get credentials from environment if not provided
    username = args.username or os.environ.get('BITBUCKET_USERNAME')
    app_password = args.app_password or os.environ.get('BITBUCKET_APP_PASSWORD')
    oauth_key = args.oauth_key or os.environ.get('BITBUCKET_OAUTH_KEY')
    oauth_secret = args.oauth_secret or os.environ.get('BITBUCKET_OAUTH_SECRET')
    
    server = BitbucketMCPServer(
        url=args.bitbucket_url,
        username=username,
        app_password=app_password,
        oauth_key=oauth_key,
        oauth_secret=oauth_secret,
        cloud=not args.server,
        host=args.host,
        port=args.port,
        transport=args.transport,
        debug=args.debug
    )
    
    print(f"Starting Bitbucket MCP Server on {args.host}:{args.port}")
    print(f"Bitbucket URL: {args.bitbucket_url}")
    print(f"Mode: {'Server' if args.server else 'Cloud'}")
    print(f"Transport: {args.transport}")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down Bitbucket MCP Server...")
    except Exception as e:
        print(f"Error: {e}")