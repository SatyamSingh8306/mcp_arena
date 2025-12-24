from mcp.server.fastmcp import FastMCP
from github import Github, GithubException, PullRequest, Repository, Issue, Branch, Commit
from typing import Literal, Annotated, Optional, List, Dict, Any
from datetime import datetime
import os
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
from mcp_arena.mcp.server import BaseMCPServer

class IssueState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


class PullRequestState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


@dataclass
class RepositoryInfo:
    name: str
    full_name: str
    description: Optional[str]
    owner: str
    private: bool
    fork: bool
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    size: int
    stargazers_count: int
    watchers_count: int
    language: Optional[str]
    forks_count: int
    open_issues_count: int
    default_branch: str
    topics: List[str]
    archived: bool
    disabled: bool


@dataclass
class IssueInfo:
    number: int
    title: str
    state: str
    body: Optional[str]
    user: str
    assignees: List[str]
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    comments: int
    pull_request: Optional[Dict[str, Any]]


@dataclass
class PullRequestInfo:
    number: int
    title: str
    state: str
    body: Optional[str]
    user: str
    assignees: List[str]
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    merged_at: Optional[datetime]
    mergeable: bool
    mergeable_state: str
    merged: bool
    base_branch: str
    head_branch: str
    draft: bool
    review_comments: int
    commits: int
    additions: int
    deletions: int
    changed_files: int


@dataclass
class BranchInfo:
    name: str
    protected: bool
    commit_sha: str
    commit_message: str
    commit_author: str
    commit_date: datetime


@dataclass
class CommitInfo:
    sha: str
    message: str
    author: str
    author_email: str
    committer: str
    committer_email: str
    date: datetime
    parents: List[str]
    stats: Dict[str, int]
    files_changed: List[str]


@dataclass
class FileContent:
    path: str
    content: str
    encoding: str
    size: int
    sha: str

class GithubMCPServer(BaseMCPServer):
    """GitHub MCP Server for managing repositories, issues, pull requests, and more."""
    
    def __init__(
        self,
        token: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize GitHub MCP Server.
        
        Args:
            token: GitHub Personal Access Token. If not provided, will try to get from GITHUB_TOKEN env var.
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.__token = token or os.getenv("GITHUB_TOKEN")
        if not self.__token:
            raise ValueError(
                "GitHub token is required. Provide it as argument or set GITHUB_TOKEN environment variable."
            )
        
        self.github = Github(self.__token)
        self.user = self.github.get_user()

        super().__init__(
            name="GitHub MCP Server",
            description="A comprehensive GitHub MCP server for managing repositories, issues, pull requests, and more.",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all GitHub-related tools."""
        self._register_user_tools()
        self._register_repository_tools()
        self._register_issue_tools()
        self._register_pull_request_tools()
        self._register_branch_tools()
        self._register_commit_tools()
        self._register_file_tools()
        self._register_organization_tools()
        self._register_webhook_tools()
        self._register_workflow_tools()

    # ========== USER TOOLS ==========
    def _register_user_tools(self):
        @self.mcp_server.tool()
        def get_user_info(
            username: Annotated[Optional[str], "GitHub username. If not provided, returns current user info"] = None
        ) -> Dict[str, Any]:
            """Get information about a GitHub user"""
            try:
                user = self.github.get_user(username) if username else self.user
                return {
                    "login": user.login,
                    "name": user.name,
                    "email": user.email,
                    "bio": user.bio,
                    "company": user.company,
                    "location": user.location,
                    "avatar_url": user.avatar_url,
                    "html_url": user.html_url,
                    "public_repos": user.public_repos,
                    "followers": user.followers,
                    "following": user.following,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                }
            except GithubException as e:
                return {"error": f"Failed to get user info: {str(e)}"}

        @self.mcp_server.tool()
        def search_users(
            query: Annotated[str, "Search query for users"],
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """Search for GitHub users"""
            try:
                users = self.github.search_users(query=query)
                results = []
                for user in users[:per_page]:
                    results.append({
                        "login": user.login,
                        "name": user.name,
                        "bio": user.bio,
                        "location": user.location,
                        "followers": user.followers,
                        "public_repos": user.public_repos
                    })
                return {
                    "total_count": users.totalCount,
                    "results": results,
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to search users: {str(e)}"}

    # ========== REPOSITORY TOOLS ==========
    def _register_repository_tools(self):
        @self.mcp_server.tool()
        def get_repository(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"]
        ) -> Dict[str, Any]:
            """Get detailed information about a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                repo_info = RepositoryInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    description=repo.description,
                    owner=repo.owner.login,
                    private=repo.private,
                    fork=repo.fork,
                    created_at=repo.created_at,
                    updated_at=repo.updated_at,
                    pushed_at=repo.pushed_at,
                    size=repo.size,
                    stargazers_count=repo.stargazers_count,
                    watchers_count=repo.watchers_count,
                    language=repo.language,
                    forks_count=repo.forks_count,
                    open_issues_count=repo.open_issues_count,
                    default_branch=repo.default_branch,
                    topics=repo.get_topics(),
                    archived=repo.archived,
                    disabled=repo.disabled
                )
                return asdict(repo_info)
            except GithubException as e:
                return {"error": f"Failed to get repository: {str(e)}"}

        @self.mcp_server.tool()
        def list_user_repositories(
            username: Annotated[Optional[str], "GitHub username. If not provided, uses current user"] = None,
            repo_type: Annotated[Literal["all", "owner", "member", "public", "private", "forks", "sources"], 
                               "Type of repositories to list"] = "all",
            sort: Annotated[Literal["created", "updated", "pushed", "full_name"], "Sort order"] = "full_name",
            direction: Annotated[Literal["asc", "desc"], "Sort direction"] = "asc",
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List repositories for a user"""
            try:
                user = self.github.get_user(username) if username else self.user
                repos = user.get_repos(
                    type=repo_type,
                    sort=sort,
                    direction=direction
                )
                
                results = []
                for repo in repos:
                    results.append({
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "description": repo.description,
                        "private": repo.private,
                        "fork": repo.fork,
                        "language": repo.language,
                        "stargazers_count": repo.stargazers_count,
                        "forks_count": repo.forks_count,
                        "open_issues_count": repo.open_issues_count,
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                        "html_url": repo.html_url
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "user": user.login,
                    "repositories": results,
                    "total_count": repos.totalCount if hasattr(repos, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list repositories: {str(e)}"}

        @self.mcp_server.tool()
        def create_repository(
            name: Annotated[str, "Repository name"],
            description: Annotated[Optional[str], "Repository description"] = None,
            private: Annotated[bool, "Whether the repository should be private"] = False,
            auto_init: Annotated[bool, "Initialize with README"] = False,
            gitignore_template: Annotated[Optional[str], "Gitignore template"] = None,
            license_template: Annotated[Optional[str], "License template"] = None,
            team_id: Annotated[Optional[int], "Team ID for organization repository"] = None
        ) -> Dict[str, Any]:
            """Create a new repository"""
            try:
                repo = self.user.create_repo(
                    name=name,
                    description=description,
                    private=private,
                    auto_init=auto_init,
                    gitignore_template=gitignore_template,
                    license_template=license_template
                )
                return {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None
                }
            except GithubException as e:
                return {"error": f"Failed to create repository: {str(e)}"}

        @self.mcp_server.tool()
        def delete_repository(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"]
        ) -> Dict[str, Any]:
            """Delete a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                # Check if user has permission
                if repo.permissions and repo.permissions.admin:
                    repo.delete()
                    return {"success": True, "message": f"Repository {repo_full_name} deleted successfully"}
                else:
                    return {"error": "Insufficient permissions to delete repository"}
            except GithubException as e:
                return {"error": f"Failed to delete repository: {str(e)}"}

        @self.mcp_server.tool()
        def fork_repository(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            organization: Annotated[Optional[str], "Organization to fork to"] = None
        ) -> Dict[str, Any]:
            """Fork a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                if organization:
                    org = self.github.get_organization(organization)
                    forked_repo = org.create_fork(repo)
                else:
                    forked_repo = self.user.create_fork(repo)
                
                return {
                    "name": forked_repo.name,
                    "full_name": forked_repo.full_name,
                    "owner": forked_repo.owner.login,
                    "fork": forked_repo.fork,
                    "parent": repo.full_name,
                    "html_url": forked_repo.html_url,
                    "clone_url": forked_repo.clone_url
                }
            except GithubException as e:
                return {"error": f"Failed to fork repository: {str(e)}"}

        @self.mcp_server.tool()
        def search_repositories(
            query: Annotated[str, "Search query for repositories"],
            sort: Annotated[Literal["stars", "forks", "help-wanted-issues", "updated"], "Sort order"] = "stars",
            order: Annotated[Literal["desc", "asc"], "Sort direction"] = "desc",
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """Search for GitHub repositories"""
            try:
                repos = self.github.search_repositories(query=query, sort=sort, order=order)
                results = []
                for repo in repos[:per_page]:
                    results.append({
                        "full_name": repo.full_name,
                        "description": repo.description,
                        "language": repo.language,
                        "stargazers_count": repo.stargazers_count,
                        "forks_count": repo.forks_count,
                        "open_issues_count": repo.open_issues_count,
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                        "html_url": repo.html_url,
                        "owner": repo.owner.login
                    })
                return {
                    "total_count": repos.totalCount,
                    "results": results,
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to search repositories: {str(e)}"}

    # ========== ISSUE TOOLS ==========
    def _register_issue_tools(self):
        @self.mcp_server.tool()
        def list_issues(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            state: Annotated[IssueState, "State of issues to list"] = IssueState.OPEN,
            labels: Annotated[Optional[List[str]], "Filter by labels"] = None,
            assignee: Annotated[Optional[str], "Filter by assignee"] = None,
            creator: Annotated[Optional[str], "Filter by creator"] = None,
            mentioned: Annotated[Optional[str], "Filter by mentioned user"] = None,
            sort: Annotated[Literal["created", "updated", "comments"], "Sort order"] = "created",
            direction: Annotated[Literal["asc", "desc"], "Sort direction"] = "desc",
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List issues in a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                issues = repo.get_issues(
                    state=state.value,
                    labels=labels,
                    assignee=assignee,
                    creator=creator,
                    mentioned=mentioned,
                    sort=sort,
                    direction=direction
                )
                
                results = []
                for issue in issues:
                    if not issue.pull_request:  # Skip PRs
                        issue_info = IssueInfo(
                            number=issue.number,
                            title=issue.title,
                            state=issue.state,
                            body=issue.body,
                            user=issue.user.login if issue.user else None,
                            assignees=[assignee.login for assignee in issue.assignees],
                            labels=[label.name for label in issue.labels],
                            created_at=issue.created_at,
                            updated_at=issue.updated_at,
                            closed_at=issue.closed_at,
                            comments=issue.comments,
                            pull_request=None
                        )
                        results.append(asdict(issue_info))
                    if len(results) >= per_page:
                        break
                
                return {
                    "repository": repo.full_name,
                    "issues": results,
                    "total_count": issues.totalCount if hasattr(issues, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list issues: {str(e)}"}

        @self.mcp_server.tool()
        def get_issue(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            issue_number: Annotated[int, "Issue number"]
        ) -> Dict[str, Any]:
            """Get detailed information about an issue"""
            try:
                repo = self.github.get_repo(repo_full_name)
                issue = repo.get_issue(issue_number)
                
                issue_info = IssueInfo(
                    number=issue.number,
                    title=issue.title,
                    state=issue.state,
                    body=issue.body,
                    user=issue.user.login if issue.user else None,
                    assignees=[assignee.login for assignee in issue.assignees],
                    labels=[label.name for label in issue.labels],
                    created_at=issue.created_at,
                    updated_at=issue.updated_at,
                    closed_at=issue.closed_at,
                    comments=issue.comments,
                    pull_request=issue.raw_data.get("pull_request") if hasattr(issue, 'raw_data') else None
                )
                return asdict(issue_info)
            except GithubException as e:
                return {"error": f"Failed to get issue: {str(e)}"}

        @self.mcp_server.tool()
        def create_issue(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            title: Annotated[str, "Issue title"],
            body: Annotated[Optional[str], "Issue body/description"] = None,
            assignees: Annotated[Optional[List[str]], "List of assignee usernames"] = None,
            labels: Annotated[Optional[List[str]], "List of label names"] = None,
            milestone: Annotated[Optional[int], "Milestone number"] = None
        ) -> Dict[str, Any]:
            """Create a new issue"""
            try:
                repo = self.github.get_repo(repo_full_name)
                issue = repo.create_issue(
                    title=title,
                    body=body,
                    assignees=assignees,
                    labels=labels,
                    milestone=milestone
                )
                
                issue_info = IssueInfo(
                    number=issue.number,
                    title=issue.title,
                    state=issue.state,
                    body=issue.body,
                    user=issue.user.login if issue.user else None,
                    assignees=[assignee.login for assignee in issue.assignees],
                    labels=[label.name for label in issue.labels],
                    created_at=issue.created_at,
                    updated_at=issue.updated_at,
                    closed_at=issue.closed_at,
                    comments=issue.comments,
                    pull_request=None
                )
                return asdict(issue_info)
            except GithubException as e:
                return {"error": f"Failed to create issue: {str(e)}"}

        @self.mcp_server.tool()
        def update_issue(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            issue_number: Annotated[int, "Issue number"],
            title: Annotated[Optional[str], "New issue title"] = None,
            body: Annotated[Optional[str], "New issue body"] = None,
            state: Annotated[Optional[Literal["open", "closed"]], "New issue state"] = None,
            assignees: Annotated[Optional[List[str]], "New list of assignees"] = None,
            labels: Annotated[Optional[List[str]], "New list of labels"] = None,
            milestone: Annotated[Optional[int], "New milestone number"] = None
        ) -> Dict[str, Any]:
            """Update an existing issue"""
            try:
                repo = self.github.get_repo(repo_full_name)
                issue = repo.get_issue(issue_number)
                
                # Update issue
                if title is not None:
                    issue.edit(title=title)
                if body is not None:
                    issue.edit(body=body)
                if state is not None:
                    issue.edit(state=state)
                if assignees is not None:
                    issue.edit(assignees=assignees)
                if labels is not None:
                    issue.edit(labels=labels)
                if milestone is not None:
                    issue.edit(milestone=milestone)
                
                # Refresh issue data
                issue = repo.get_issue(issue_number)
                issue_info = IssueInfo(
                    number=issue.number,
                    title=issue.title,
                    state=issue.state,
                    body=issue.body,
                    user=issue.user.login if issue.user else None,
                    assignees=[assignee.login for assignee in issue.assignees],
                    labels=[label.name for label in issue.labels],
                    created_at=issue.created_at,
                    updated_at=issue.updated_at,
                    closed_at=issue.closed_at,
                    comments=issue.comments,
                    pull_request=issue.raw_data.get("pull_request") if hasattr(issue, 'raw_data') else None
                )
                return asdict(issue_info)
            except GithubException as e:
                return {"error": f"Failed to update issue: {str(e)}"}

        @self.mcp_server.tool()
        def add_issue_comment(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            issue_number: Annotated[int, "Issue number"],
            comment: Annotated[str, "Comment text"]
        ) -> Dict[str, Any]:
            """Add a comment to an issue"""
            try:
                repo = self.github.get_repo(repo_full_name)
                issue = repo.get_issue(issue_number)
                comment_obj = issue.create_comment(comment)
                
                return {
                    "id": comment_obj.id,
                    "user": comment_obj.user.login if comment_obj.user else None,
                    "body": comment_obj.body,
                    "created_at": comment_obj.created_at.isoformat() if comment_obj.created_at else None,
                    "updated_at": comment_obj.updated_at.isoformat() if comment_obj.updated_at else None,
                    "html_url": comment_obj.html_url
                }
            except GithubException as e:
                return {"error": f"Failed to add comment: {str(e)}"}

        @self.mcp_server.tool()
        def list_issue_comments(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            issue_number: Annotated[int, "Issue number"],
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List comments on an issue"""
            try:
                repo = self.github.get_repo(repo_full_name)
                issue = repo.get_issue(issue_number)
                comments = issue.get_comments()
                
                results = []
                for comment in comments:
                    results.append({
                        "id": comment.id,
                        "user": comment.user.login if comment.user else None,
                        "body": comment.body,
                        "created_at": comment.created_at.isoformat() if comment.created_at else None,
                        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                        "html_url": comment.html_url
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "issue_number": issue_number,
                    "comments": results,
                    "total_count": comments.totalCount if hasattr(comments, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list comments: {str(e)}"}

    # ========== PULL REQUEST TOOLS ==========
    def _register_pull_request_tools(self):
        @self.mcp_server.tool()
        def list_pull_requests(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            state: Annotated[PullRequestState, "State of PRs to list"] = PullRequestState.OPEN,
            base: Annotated[Optional[str], "Filter by base branch"] = None,
            head: Annotated[Optional[str], "Filter by head branch"] = None,
            sort: Annotated[Literal["created", "updated", "popularity", "long-running"], "Sort order"] = "created",
            direction: Annotated[Literal["asc", "desc"], "Sort direction"] = "desc",
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List pull requests in a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                pull_requests = repo.get_pulls(
                    state=state.value,
                    base=base,
                    head=head,
                    sort=sort,
                    direction=direction
                )
                
                results = []
                for pr in pull_requests:
                    pr_info = PullRequestInfo(
                        number=pr.number,
                        title=pr.title,
                        state=pr.state,
                        body=pr.body,
                        user=pr.user.login if pr.user else None,
                        assignees=[assignee.login for assignee in pr.assignees],
                        labels=[label.name for label in pr.labels],
                        created_at=pr.created_at,
                        updated_at=pr.updated_at,
                        closed_at=pr.closed_at,
                        merged_at=pr.merged_at,
                        mergeable=pr.mergeable,
                        mergeable_state=pr.mergeable_state,
                        merged=pr.merged,
                        base_branch=pr.base.ref,
                        head_branch=pr.head.ref,
                        draft=pr.draft,
                        review_comments=pr.review_comments,
                        commits=pr.commits,
                        additions=pr.additions,
                        deletions=pr.deletions,
                        changed_files=pr.changed_files
                    )
                    results.append(asdict(pr_info))
                    if len(results) >= per_page:
                        break
                
                return {
                    "repository": repo.full_name,
                    "pull_requests": results,
                    "total_count": pull_requests.totalCount if hasattr(pull_requests, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list pull requests: {str(e)}"}

        @self.mcp_server.tool()
        def get_pull_request(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            pr_number: Annotated[int, "Pull request number"]
        ) -> Dict[str, Any]:
            """Get detailed information about a pull request"""
            try:
                repo = self.github.get_repo(repo_full_name)
                pr = repo.get_pull(pr_number)
                
                pr_info = PullRequestInfo(
                    number=pr.number,
                    title=pr.title,
                    state=pr.state,
                    body=pr.body,
                    user=pr.user.login if pr.user else None,
                    assignees=[assignee.login for assignee in pr.assignees],
                    labels=[label.name for label in pr.labels],
                    created_at=pr.created_at,
                    updated_at=pr.updated_at,
                    closed_at=pr.closed_at,
                    merged_at=pr.merged_at,
                    mergeable=pr.mergeable,
                    mergeable_state=pr.mergeable_state,
                    merged=pr.merged,
                    base_branch=pr.base.ref,
                    head_branch=pr.head.ref,
                    draft=pr.draft,
                    review_comments=pr.review_comments,
                    commits=pr.commits,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    changed_files=pr.changed_files
                )
                return asdict(pr_info)
            except GithubException as e:
                return {"error": f"Failed to get pull request: {str(e)}"}

        @self.mcp_server.tool()
        def create_pull_request(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            title: Annotated[str, "Pull request title"],
            head: Annotated[str, "Head branch (the branch with your changes)"],
            base: Annotated[str, "Base branch (the branch to merge into)"],
            body: Annotated[Optional[str], "Pull request description"] = None,
            draft: Annotated[bool, "Whether to create as draft"] = False,
            maintainer_can_modify: Annotated[bool, "Allow maintainers to modify"] = True
        ) -> Dict[str, Any]:
            """Create a new pull request"""
            try:
                repo = self.github.get_repo(repo_full_name)
                pr = repo.create_pull(
                    title=title,
                    body=body,
                    head=head,
                    base=base,
                    draft=draft,
                    maintainer_can_modify=maintainer_can_modify
                )
                
                pr_info = PullRequestInfo(
                    number=pr.number,
                    title=pr.title,
                    state=pr.state,
                    body=pr.body,
                    user=pr.user.login if pr.user else None,
                    assignees=[assignee.login for assignee in pr.assignees],
                    labels=[label.name for label in pr.labels],
                    created_at=pr.created_at,
                    updated_at=pr.updated_at,
                    closed_at=pr.closed_at,
                    merged_at=pr.merged_at,
                    mergeable=pr.mergeable,
                    mergeable_state=pr.mergeable_state,
                    merged=pr.merged,
                    base_branch=pr.base.ref,
                    head_branch=pr.head.ref,
                    draft=pr.draft,
                    review_comments=pr.review_comments,
                    commits=pr.commits,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    changed_files=pr.changed_files
                )
                return asdict(pr_info)
            except GithubException as e:
                return {"error": f"Failed to create pull request: {str(e)}"}

        @self.mcp_server.tool()
        def update_pull_request(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            pr_number: Annotated[int, "Pull request number"],
            title: Annotated[Optional[str], "New title"] = None,
            body: Annotated[Optional[str], "New body"] = None,
            state: Annotated[Optional[Literal["open", "closed"]], "New state"] = None,
            base: Annotated[Optional[str], "New base branch"] = None,
            maintainer_can_modify: Annotated[Optional[bool], "Allow maintainers to modify"] = None
        ) -> Dict[str, Any]:
            """Update a pull request"""
            try:
                repo = self.github.get_repo(repo_full_name)
                pr = repo.get_pull(pr_number)
                
                # Update PR
                pr.edit(
                    title=title if title is not None else pr.title,
                    body=body if body is not None else pr.body,
                    state=state if state is not None else pr.state,
                    base=base if base is not None else pr.base.ref,
                    maintainer_can_modify=maintainer_can_modify if maintainer_can_modify is not None else pr.maintainer_can_modify
                )
                
                # Refresh PR data
                pr = repo.get_pull(pr_number)
                pr_info = PullRequestInfo(
                    number=pr.number,
                    title=pr.title,
                    state=pr.state,
                    body=pr.body,
                    user=pr.user.login if pr.user else None,
                    assignees=[assignee.login for assignee in pr.assignees],
                    labels=[label.name for label in pr.labels],
                    created_at=pr.created_at,
                    updated_at=pr.updated_at,
                    closed_at=pr.closed_at,
                    merged_at=pr.merged_at,
                    mergeable=pr.mergeable,
                    mergeable_state=pr.mergeable_state,
                    merged=pr.merged,
                    base_branch=pr.base.ref,
                    head_branch=pr.head.ref,
                    draft=pr.draft,
                    review_comments=pr.review_comments,
                    commits=pr.commits,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    changed_files=pr.changed_files
                )
                return asdict(pr_info)
            except GithubException as e:
                return {"error": f"Failed to update pull request: {str(e)}"}

        @self.mcp_server.tool()
        def merge_pull_request(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            pr_number: Annotated[int, "Pull request number"],
            commit_message: Annotated[Optional[str], "Commit message for the merge"] = None,
            merge_method: Annotated[Literal["merge", "squash", "rebase"], "Merge method"] = "merge"
        ) -> Dict[str, Any]:
            """Merge a pull request"""
            try:
                repo = self.github.get_repo(repo_full_name)
                pr = repo.get_pull(pr_number)
                
                if not pr.mergeable:
                    return {"error": "Pull request is not mergeable", "mergeable_state": pr.mergeable_state}
                
                merge_result = pr.merge(
                    commit_message=commit_message,
                    merge_method=merge_method
                )
                
                return {
                    "merged": merge_result.merged,
                    "message": merge_result.message,
                    "sha": merge_result.sha,
                    "html_url": merge_result.html_url if hasattr(merge_result, 'html_url') else None
                }
            except GithubException as e:
                return {"error": f"Failed to merge pull request: {str(e)}"}

        @self.mcp_server.tool()
        def list_pull_request_files(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            pr_number: Annotated[int, "Pull request number"],
            per_page: Annotated[int, "Number of results per page"] = 100,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List files changed in a pull request"""
            try:
                repo = self.github.get_repo(repo_full_name)
                pr = repo.get_pull(pr_number)
                files = pr.get_files()
                
                results = []
                for file in files:
                    results.append({
                        "filename": file.filename,
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "changes": file.changes,
                        "patch": file.patch[:500] + "..." if file.patch and len(file.patch) > 500 else file.patch if file.patch else None,
                        "raw_url": file.raw_url
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "pull_request": pr_number,
                    "files": results,
                    "total_count": files.totalCount if hasattr(files, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list PR files: {str(e)}"}

        @self.mcp_server.tool()
        def list_pull_request_reviews(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            pr_number: Annotated[int, "Pull request number"],
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List reviews for a pull request"""
            try:
                repo = self.github.get_repo(repo_full_name)
                pr = repo.get_pull(pr_number)
                reviews = pr.get_reviews()
                
                results = []
                for review in reviews:
                    results.append({
                        "id": review.id,
                        "user": review.user.login if review.user else None,
                        "body": review.body,
                        "state": review.state,
                        "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
                        "commit_id": review.commit_id,
                        "html_url": review.html_url
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "pull_request": pr_number,
                    "reviews": results,
                    "total_count": reviews.totalCount if hasattr(reviews, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list PR reviews: {str(e)}"}

    # ========== BRANCH TOOLS ==========
    def _register_branch_tools(self):
        @self.mcp_server.tool()
        def list_branches(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List branches in a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                branches = repo.get_branches()
                
                results = []
                for branch in branches:
                    branch_info = BranchInfo(
                        name=branch.name,
                        protected=branch.protected,
                        commit_sha=branch.commit.sha,
                        commit_message=branch.commit.commit.message,
                        commit_author=branch.commit.commit.author.name if branch.commit.commit.author else None,
                        commit_date=branch.commit.commit.author.date if branch.commit.commit.author else None
                    )
                    results.append(asdict(branch_info))
                    if len(results) >= per_page:
                        break
                
                return {
                    "repository": repo.full_name,
                    "branches": results,
                    "total_count": branches.totalCount if hasattr(branches, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list branches: {str(e)}"}

        @self.mcp_server.tool()
        def get_branch(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            branch_name: Annotated[str, "Branch name"]
        ) -> Dict[str, Any]:
            """Get detailed information about a branch"""
            try:
                repo = self.github.get_repo(repo_full_name)
                branch = repo.get_branch(branch_name)
                
                branch_info = BranchInfo(
                    name=branch.name,
                    protected=branch.protected,
                    commit_sha=branch.commit.sha,
                    commit_message=branch.commit.commit.message,
                    commit_author=branch.commit.commit.author.name if branch.commit.commit.author else None,
                    commit_date=branch.commit.commit.author.date if branch.commit.commit.author else None
                )
                return asdict(branch_info)
            except GithubException as e:
                return {"error": f"Failed to get branch: {str(e)}"}

        @self.mcp_server.tool()
        def create_branch(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            branch_name: Annotated[str, "New branch name"],
            from_branch: Annotated[str, "Source branch name"] = "main"
        ) -> Dict[str, Any]:
            """Create a new branch from an existing branch"""
            try:
                repo = self.github.get_repo(repo_full_name)
                source_branch = repo.get_branch(from_branch)
                
                # Create new branch
                repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=source_branch.commit.sha
                )
                
                # Get the new branch
                new_branch = repo.get_branch(branch_name)
                branch_info = BranchInfo(
                    name=new_branch.name,
                    protected=new_branch.protected,
                    commit_sha=new_branch.commit.sha,
                    commit_message=new_branch.commit.commit.message,
                    commit_author=new_branch.commit.commit.author.name if new_branch.commit.commit.author else None,
                    commit_date=new_branch.commit.commit.author.date if new_branch.commit.commit.author else None
                )
                return asdict(branch_info)
            except GithubException as e:
                return {"error": f"Failed to create branch: {str(e)}"}

        @self.mcp_server.tool()
        def delete_branch(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            branch_name: Annotated[str, "Branch name to delete"]
        ) -> Dict[str, Any]:
            """Delete a branch"""
            try:
                repo = self.github.get_repo(repo_full_name)
                
                # Check if branch exists and is not protected
                branch = repo.get_branch(branch_name)
                if branch.protected:
                    return {"error": "Cannot delete a protected branch"}
                
                # Delete the branch
                ref = repo.get_git_ref(f"heads/{branch_name}")
                ref.delete()
                
                return {"success": True, "message": f"Branch {branch_name} deleted successfully"}
            except GithubException as e:
                return {"error": f"Failed to delete branch: {str(e)}"}

        @self.mcp_server.tool()
        def update_branch_protection(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            branch_name: Annotated[str, "Branch name"],
            require_reviews: Annotated[bool, "Require pull request reviews"] = True,
            required_approving_review_count: Annotated[int, "Required number of approving reviews"] = 1,
            dismiss_stale_reviews: Annotated[bool, "Dismiss stale pull request reviews"] = True,
            require_code_owner_reviews: Annotated[bool, "Require review from code owners"] = False,
            require_status_checks: Annotated[bool, "Require status checks to pass"] = True,
            required_status_checks: Annotated[Optional[List[str]], "List of required status check contexts"] = None,
            require_branches_up_to_date: Annotated[bool, "Require branches to be up to date"] = True,
            enforce_admins: Annotated[bool, "Enforce restrictions for admins"] = False,
            restrictions: Annotated[Optional[Dict[str, List[str]]], "Restrictions for pushing"] = None
        ) -> Dict[str, Any]:
            """Update branch protection rules"""
            try:
                repo = self.github.get_repo(repo_full_name)
                branch = repo.get_branch(branch_name)
                
                # Build protection settings
                protection = {
                    "required_pull_request_reviews": {
                        "required_approving_review_count": required_approving_review_count,
                        "dismiss_stale_reviews": dismiss_stale_reviews,
                        "require_code_owner_reviews": require_code_owner_reviews
                    } if require_reviews else None,
                    "required_status_checks": {
                        "strict": require_branches_up_to_date,
                        "contexts": required_status_checks or []
                    } if require_status_checks else None,
                    "enforce_admins": enforce_admins,
                    "restrictions": restrictions
                }
                
                branch.edit_protection(**protection)
                return {"success": True, "message": f"Protection updated for branch {branch_name}"}
            except GithubException as e:
                return {"error": f"Failed to update branch protection: {str(e)}"}

    # ========== COMMIT TOOLS ==========
    def _register_commit_tools(self):
        @self.mcp_server.tool()
        def list_commits(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            branch: Annotated[Optional[str], "Branch name"] = None,
            path: Annotated[Optional[str], "File path to filter commits"] = None,
            author: Annotated[Optional[str], "Filter by author"] = None,
            since: Annotated[Optional[str], "Filter commits since date (ISO format)"] = None,
            until: Annotated[Optional[str], "Filter commits until date (ISO format)"] = None,
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List commits in a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                commits = repo.get_commits(
                    sha=branch,
                    path=path,
                    author=author,
                    since=since,
                    until=until
                )
                
                results = []
                for commit in commits:
                    stats = commit.stats
                    commit_info = CommitInfo(
                        sha=commit.sha,
                        message=commit.commit.message,
                        author=commit.commit.author.name if commit.commit.author else None,
                        author_email=commit.commit.author.email if commit.commit.author else None,
                        committer=commit.commit.committer.name if commit.commit.committer else None,
                        committer_email=commit.commit.committer.email if commit.commit.committer else None,
                        date=commit.commit.author.date if commit.commit.author else commit.commit.committer.date,
                        parents=[parent.sha for parent in commit.parents],
                        stats={
                            "total": stats.total,
                            "additions": stats.additions,
                            "deletions": stats.deletions
                        } if stats else {},
                        files_changed=[file.filename for file in commit.files] if commit.files else []
                    )
                    results.append(asdict(commit_info))
                    if len(results) >= per_page:
                        break
                
                return {
                    "repository": repo.full_name,
                    "commits": results,
                    "total_count": commits.totalCount if hasattr(commits, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list commits: {str(e)}"}

        @self.mcp_server.tool()
        def get_commit(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            commit_sha: Annotated[str, "Commit SHA"]
        ) -> Dict[str, Any]:
            """Get detailed information about a commit"""
            try:
                repo = self.github.get_repo(repo_full_name)
                commit = repo.get_commit(commit_sha)
                
                stats = commit.stats
                commit_info = CommitInfo(
                    sha=commit.sha,
                    message=commit.commit.message,
                    author=commit.commit.author.name if commit.commit.author else None,
                    author_email=commit.commit.author.email if commit.commit.author else None,
                    committer=commit.commit.committer.name if commit.commit.committer else None,
                    committer_email=commit.commit.committer.email if commit.commit.committer else None,
                    date=commit.commit.author.date if commit.commit.author else commit.commit.committer.date,
                    parents=[parent.sha for parent in commit.parents],
                    stats={
                        "total": stats.total,
                        "additions": stats.additions,
                        "deletions": stats.deletions
                    } if stats else {},
                    files_changed=[file.filename for file in commit.files] if commit.files else []
                )
                return asdict(commit_info)
            except GithubException as e:
                return {"error": f"Failed to get commit: {str(e)}"}

        @self.mcp_server.tool()
        def create_commit(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            message: Annotated[str, "Commit message"],
            content: Annotated[str, "File content"],
            path: Annotated[str, "File path"],
            branch: Annotated[str, "Branch name"] = "main",
            author_name: Annotated[Optional[str], "Author name"] = None,
            author_email: Annotated[Optional[str], "Author email"] = None
        ) -> Dict[str, Any]:
            """Create a new commit with file changes"""
            try:
                repo = self.github.get_repo(repo_full_name)
                
                # Get current commit
                branch_ref = repo.get_branch(branch)
                base_tree = repo.get_git_tree(branch_ref.commit.sha)
                
                # Create blob with file content
                blob = repo.create_git_blob(content, "utf-8")
                
                # Create new tree
                elements = [{
                    "path": path,
                    "mode": "100644",  # File mode
                    "type": "blob",
                    "sha": blob.sha
                }]
                
                tree = repo.create_git_tree(elements, base_tree)
                
                # Create commit
                author = None
                if author_name and author_email:
                    author = InputGitAuthor(author_name, author_email)
                
                commit = repo.create_git_commit(
                    message=message,
                    tree=tree.sha,
                    parents=[branch_ref.commit.sha],
                    author=author,
                    committer=author
                )
                
                # Update branch reference
                branch_ref.edit(commit.sha)
                
                return {
                    "sha": commit.sha,
                    "message": commit.message,
                    "author": author_name,
                    "tree_sha": tree.sha,
                    "parent_sha": branch_ref.commit.sha,
                    "html_url": f"{repo.html_url}/commit/{commit.sha}"
                }
            except GithubException as e:
                return {"error": f"Failed to create commit: {str(e)}"}

    # ========== FILE TOOLS ==========
    def _register_file_tools(self):
        @self.mcp_server.tool()
        def get_file_content(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            path: Annotated[str, "File path in repository"],
            ref: Annotated[Optional[str], "Branch/Tag/Commit SHA"] = None
        ) -> Dict[str, Any]:
            """Get content of a file from repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                file_content = repo.get_contents(path, ref=ref)
                
                file_info = FileContent(
                    path=file_content.path,
                    content=file_content.decoded_content.decode('utf-8') if file_content.encoding == 'base64' else file_content.content,
                    encoding=file_content.encoding,
                    size=file_content.size,
                    sha=file_content.sha
                )
                return asdict(file_info)
            except GithubException as e:
                return {"error": f"Failed to get file content: {str(e)}"}

        @self.mcp_server.tool()
        def create_file(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            path: Annotated[str, "File path in repository"],
            content: Annotated[str, "File content"],
            message: Annotated[str, "Commit message"],
            branch: Annotated[str, "Branch name"] = "main"
        ) -> Dict[str, Any]:
            """Create a new file in repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                result = repo.create_file(
                    path=path,
                    message=message,
                    content=content,
                    branch=branch
                )
                
                return {
                    "path": result["content"].path,
                    "sha": result["commit"].sha,
                    "commit_message": result["commit"].commit.message,
                    "html_url": result["content"].html_url
                }
            except GithubException as e:
                return {"error": f"Failed to create file: {str(e)}"}

        @self.mcp_server.tool()
        def update_file(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            path: Annotated[str, "File path in repository"],
            content: Annotated[str, "New file content"],
            message: Annotated[str, "Commit message"],
            sha: Annotated[str, "SHA of the file being replaced"],
            branch: Annotated[str, "Branch name"] = "main"
        ) -> Dict[str, Any]:
            """Update an existing file in repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                result = repo.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=sha,
                    branch=branch
                )
                
                return {
                    "path": result["content"].path,
                    "sha": result["commit"].sha,
                    "commit_message": result["commit"].commit.message,
                    "html_url": result["content"].html_url
                }
            except GithubException as e:
                return {"error": f"Failed to update file: {str(e)}"}

        @self.mcp_server.tool()
        def delete_file(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            path: Annotated[str, "File path in repository"],
            message: Annotated[str, "Commit message"],
            sha: Annotated[str, "SHA of the file being deleted"],
            branch: Annotated[str, "Branch name"] = "main"
        ) -> Dict[str, Any]:
            """Delete a file from repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                result = repo.delete_file(
                    path=path,
                    message=message,
                    sha=sha,
                    branch=branch
                )
                
                return {
                    "path": path,
                    "sha": result["commit"].sha,
                    "commit_message": result["commit"].commit.message,
                    "deleted": True
                }
            except GithubException as e:
                return {"error": f"Failed to delete file: {str(e)}"}

        @self.mcp_server.tool()
        def list_directory(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            path: Annotated[str, "Directory path"] = "",
            ref: Annotated[Optional[str], "Branch/Tag/Commit SHA"] = None,
            recursive: Annotated[bool, "List recursively"] = False
        ) -> Dict[str, Any]:
            """List contents of a directory"""
            try:
                repo = self.github.get_repo(repo_full_name)
                contents = repo.get_contents(path, ref=ref)
                
                if recursive:
                    all_contents = []
                    while contents:
                        file_content = contents.pop(0)
                        if file_content.type == "dir":
                            contents.extend(repo.get_contents(file_content.path, ref=ref))
                        else:
                            all_contents.append(file_content)
                    contents = all_contents
                
                results = []
                for item in contents:
                    results.append({
                        "name": item.name,
                        "path": item.path,
                        "type": item.type,
                        "size": item.size,
                        "sha": item.sha,
                        "html_url": item.html_url,
                        "download_url": item.download_url
                    })
                
                return {
                    "directory": path,
                    "contents": results,
                    "total_count": len(results)
                }
            except GithubException as e:
                return {"error": f"Failed to list directory: {str(e)}"}

    # ========== ORGANIZATION TOOLS ==========
    def _register_organization_tools(self):
        @self.mcp_server.tool()
        def get_organization(
            org_name: Annotated[str, "Organization name"]
        ) -> Dict[str, Any]:
            """Get information about an organization"""
            try:
                org = self.github.get_organization(org_name)
                return {
                    "login": org.login,
                    "name": org.name,
                    "description": org.description,
                    "email": org.email,
                    "location": org.location,
                    "avatar_url": org.avatar_url,
                    "html_url": org.html_url,
                    "public_repos": org.public_repos,
                    "total_private_repos": org.total_private_repos,
                    "created_at": org.created_at.isoformat() if org.created_at else None,
                    "updated_at": org.updated_at.isoformat() if org.updated_at else None
                }
            except GithubException as e:
                return {"error": f"Failed to get organization: {str(e)}"}

        @self.mcp_server.tool()
        def list_organization_repositories(
            org_name: Annotated[str, "Organization name"],
            repo_type: Annotated[Literal["all", "public", "private", "forks", "sources", "member"], 
                               "Type of repositories to list"] = "all",
            sort: Annotated[Literal["created", "updated", "pushed", "full_name"], "Sort order"] = "full_name",
            direction: Annotated[Literal["asc", "desc"], "Sort direction"] = "asc",
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List repositories in an organization"""
            try:
                org = self.github.get_organization(org_name)
                repos = org.get_repos(
                    type=repo_type,
                    sort=sort,
                    direction=direction
                )
                
                results = []
                for repo in repos:
                    results.append({
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "description": repo.description,
                        "private": repo.private,
                        "fork": repo.fork,
                        "language": repo.language,
                        "stargazers_count": repo.stargazers_count,
                        "forks_count": repo.forks_count,
                        "open_issues_count": repo.open_issues_count,
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                        "html_url": repo.html_url
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "organization": org.login,
                    "repositories": results,
                    "total_count": repos.totalCount if hasattr(repos, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list organization repositories: {str(e)}"}

        @self.mcp_server.tool()
        def list_organization_members(
            org_name: Annotated[str, "Organization name"],
            filter_by: Annotated[Literal["all", "2fa_disabled"], "Filter members"] = "all",
            role: Annotated[Literal["all", "admin", "member"], "Filter by role"] = "all",
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List members of an organization"""
            try:
                org = self.github.get_organization(org_name)
                members = org.get_members(
                    filter=filter_by,
                    role=role
                )
                
                results = []
                for member in members:
                    results.append({
                        "login": member.login,
                        "avatar_url": member.avatar_url,
                        "html_url": member.html_url,
                        "type": member.type
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "organization": org.login,
                    "members": results,
                    "total_count": members.totalCount if hasattr(members, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list organization members: {str(e)}"}

        @self.mcp_server.tool()
        def list_organization_teams(
            org_name: Annotated[str, "Organization name"],
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List teams in an organization"""
            try:
                org = self.github.get_organization(org_name)
                teams = org.get_teams()
                
                results = []
                for team in teams:
                    results.append({
                        "id": team.id,
                        "name": team.name,
                        "description": team.description,
                        "privacy": team.privacy,
                        "permission": team.permission,
                        "members_count": team.members_count,
                        "repos_count": team.repos_count,
                        "slug": team.slug
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "organization": org.login,
                    "teams": results,
                    "total_count": teams.totalCount if hasattr(teams, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list organization teams: {str(e)}"}

    # ========== WEBHOOK TOOLS ==========
    def _register_webhook_tools(self):
        @self.mcp_server.tool()
        def list_webhooks(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List webhooks for a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                webhooks = repo.get_hooks()
                
                results = []
                for hook in webhooks:
                    results.append({
                        "id": hook.id,
                        "name": hook.name,
                        "active": hook.active,
                        "events": hook.events,
                        "config": hook.config,
                        "url": hook.config.get("url") if hook.config else None,
                        "created_at": hook.created_at.isoformat() if hook.created_at else None,
                        "updated_at": hook.updated_at.isoformat() if hook.updated_at else None
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "repository": repo.full_name,
                    "webhooks": results,
                    "total_count": webhooks.totalCount if hasattr(webhooks, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list webhooks: {str(e)}"}

        @self.mcp_server.tool()
        def create_webhook(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            url: Annotated[str, "Webhook URL"],
            events: Annotated[List[str], "List of events to trigger webhook"] = ["push"],
            active: Annotated[bool, "Whether the webhook is active"] = True,
            content_type: Annotated[Literal["json", "form"], "Content type"] = "json",
            secret: Annotated[Optional[str], "Secret for securing webhook"] = None
        ) -> Dict[str, Any]:
            """Create a new webhook for a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                
                config = {
                    "url": url,
                    "content_type": content_type
                }
                if secret:
                    config["secret"] = secret
                
                hook = repo.create_hook(
                    name="web",
                    config=config,
                    events=events,
                    active=active
                )
                
                return {
                    "id": hook.id,
                    "name": hook.name,
                    "active": hook.active,
                    "events": hook.events,
                    "config": hook.config,
                    "url": hook.config.get("url") if hook.config else None,
                    "created_at": hook.created_at.isoformat() if hook.created_at else None
                }
            except GithubException as e:
                return {"error": f"Failed to create webhook: {str(e)}"}

        @self.mcp_server.tool()
        def delete_webhook(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            hook_id: Annotated[int, "Webhook ID"]
        ) -> Dict[str, Any]:
            """Delete a webhook"""
            try:
                repo = self.github.get_repo(repo_full_name)
                hook = repo.get_hook(hook_id)
                hook.delete()
                
                return {"success": True, "message": f"Webhook {hook_id} deleted successfully"}
            except GithubException as e:
                return {"error": f"Failed to delete webhook: {str(e)}"}

    # ========== WORKFLOW TOOLS ==========
    def _register_workflow_tools(self):
        @self.mcp_server.tool()
        def list_workflows(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List GitHub Actions workflows for a repository"""
            try:
                repo = self.github.get_repo(repo_full_name)
                workflows = repo.get_workflows()
                
                results = []
                for workflow in workflows:
                    results.append({
                        "id": workflow.id,
                        "name": workflow.name,
                        "path": workflow.path,
                        "state": workflow.state,
                        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
                        "url": workflow.url,
                        "html_url": workflow.html_url,
                        "badge_url": workflow.badge_url
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "repository": repo.full_name,
                    "workflows": results,
                    "total_count": workflows.totalCount if hasattr(workflows, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list workflows: {str(e)}"}

        @self.mcp_server.tool()
        def list_workflow_runs(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            workflow_id: Annotated[Optional[int], "Workflow ID. If not provided, lists all runs"] = None,
            actor: Annotated[Optional[str], "Filter by user who triggered the run"] = None,
            branch: Annotated[Optional[str], "Filter by branch"] = None,
            event: Annotated[Optional[str], "Filter by event that triggered the workflow"] = None,
            status: Annotated[Optional[Literal["completed", "action_required", "cancelled", "failure", "neutral", "skipped", "stale", "success", "timed_out", "in_progress", "queued", "requested", "waiting"]], 
                              "Filter by status"] = None,
            per_page: Annotated[int, "Number of results per page"] = 30,
            page: Annotated[int, "Page number"] = 1
        ) -> Dict[str, Any]:
            """List workflow runs"""
            try:
                repo = self.github.get_repo(repo_full_name)
                
                if workflow_id:
                    workflow = repo.get_workflow(workflow_id)
                    runs = workflow.get_runs(
                        actor=actor,
                        branch=branch,
                        event=event,
                        status=status
                    )
                else:
                    runs = repo.get_workflow_runs(
                        actor=actor,
                        branch=branch,
                        event=event,
                        status=status
                    )
                
                results = []
                for run in runs:
                    results.append({
                        "id": run.id,
                        "name": run.name,
                        "head_branch": run.head_branch,
                        "head_sha": run.head_sha,
                        "run_number": run.run_number,
                        "event": run.event,
                        "status": run.status,
                        "conclusion": run.conclusion,
                        "workflow_id": run.workflow_id,
                        "created_at": run.created_at.isoformat() if run.created_at else None,
                        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
                        "run_started_at": run.run_started_at.isoformat() if run.run_started_at else None,
                        "html_url": run.html_url,
                        "jobs_url": run.jobs_url,
                        "logs_url": run.logs_url
                    })
                    if len(results) >= per_page:
                        break
                
                return {
                    "repository": repo.full_name,
                    "workflow_id": workflow_id,
                    "runs": results,
                    "total_count": runs.totalCount if hasattr(runs, 'totalCount') else len(results),
                    "page": page,
                    "per_page": per_page
                }
            except GithubException as e:
                return {"error": f"Failed to list workflow runs: {str(e)}"}

        @self.mcp_server.tool()
        def trigger_workflow_dispatch(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            workflow_id: Annotated[int, "Workflow ID or workflow file name"],
            ref: Annotated[str, "Branch or tag name"] = "main",
            inputs: Annotated[Optional[Dict[str, Any]], "Input parameters for the workflow"] = None
        ) -> Dict[str, Any]:
            """Trigger a workflow dispatch event"""
            try:
                repo = self.github.get_repo(repo_full_name)
                
                if isinstance(workflow_id, int):
                    workflow = repo.get_workflow(workflow_id)
                else:
                    # workflow_id is actually the workflow file name
                    workflows = repo.get_workflows()
                    workflow = None
                    for wf in workflows:
                        if wf.path.endswith(workflow_id):
                            workflow = wf
                            break
                    
                    if not workflow:
                        return {"error": f"Workflow {workflow_id} not found"}
                
                workflow.create_dispatch(ref=ref, inputs=inputs or {})
                
                return {
                    "success": True,
                    "message": f"Workflow {workflow.name} triggered on {ref}",
                    "workflow_id": workflow.id,
                    "workflow_name": workflow.name,
                    "ref": ref,
                    "inputs": inputs
                }
            except GithubException as e:
                return {"error": f"Failed to trigger workflow: {str(e)}"}

        @self.mcp_server.tool()
        def cancel_workflow_run(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            run_id: Annotated[int, "Workflow run ID"]
        ) -> Dict[str, Any]:
            """Cancel a workflow run"""
            try:
                repo = self.github.get_repo(repo_full_name)
                run = repo.get_workflow_run(run_id)
                run.cancel()
                
                return {
                    "success": True,
                    "message": f"Workflow run {run_id} cancelled",
                    "run_id": run_id,
                    "status": "cancelled"
                }
            except GithubException as e:
                return {"error": f"Failed to cancel workflow run: {str(e)}"}

        @self.mcp_server.tool()
        def get_workflow_run_logs(
            repo_full_name: Annotated[str, "Repository full name in format 'owner/repo'"],
            run_id: Annotated[int, "Workflow run ID"]
        ) -> Dict[str, Any]:
            """Get logs for a workflow run"""
            try:
                repo = self.github.get_repo(repo_full_name)
                run = repo.get_workflow_run(run_id)
                
                # Note: This returns download URLs, not the actual logs
                logs = run.logs()
                
                return {
                    "run_id": run_id,
                    "logs_available": logs is not None,
                    "logs_url": run.logs_url if hasattr(run, 'logs_url') else None,
                    "logs_download_url": logs if logs else None
                }
            except GithubException as e:
                return {"error": f"Failed to get workflow logs: {str(e)}"}


# For InputGitAuthor if needed
try:
    from github.InputGitAuthor import InputGitAuthor
except ImportError:
    class InputGitAuthor:
        def __init__(self, name, email):
            self.name = name
            self.email = email


def main():
    """Main entry point for the GitHub MCP Server"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="GitHub MCP Server")
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub Personal Access Token (or set GITHUB_TOKEN environment variable)",
        default=os.getenv("GITHUB_TOKEN")
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=['stdio', 'sse', 'streamable-http'],
        default='stdio',
        help="Transport protocol for MCP server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host for SSE/HTTP transport"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE/HTTP transport"
    )
    
    args = parser.parse_args()
    
    if not args.token:
        print("Error: GitHub token is required. Provide --token or set GITHUB_TOKEN environment variable.")
        exit(1)
    
    try:
        server = GithubMCPServer(token=args.token)
        server.mcp_server.transport = args.transport
        if args.transport in ['sse', 'streamable-http']:
            server.mcp_server.host = args.host
            server.mcp_server.port = args.port
        
        print(f"Starting GitHub MCP Server with {args.transport} transport...")
        if args.transport in ['sse', 'streamable-http']:
            print(f"Server listening on {args.host}:{args.port}")
        
        server.run()
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(1)


if __name__ == "__main__":
    main()