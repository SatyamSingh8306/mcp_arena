from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
import gitlab
from gitlab.exceptions import GitlabError
import json
import base64
from pathlib import Path
from enum import Enum
from mcp_arena.mcp.server import BaseMCPServer

class MergeRequestState(Enum):
    """Merge request state enumeration."""
    OPENED = "opened"
    CLOSED = "closed"
    LOCKED = "locked"
    MERGED = "merged"
    ALL = "all"

class IssueState(Enum):
    """Issue state enumeration."""
    OPENED = "opened"
    CLOSED = "closed"
    ALL = "all"

class PipelineStatus(Enum):
    """Pipeline status enumeration."""
    RUNNING = "running"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    SKIPPED = "skipped"
    CREATED = "created"

@dataclass
class ProjectInfo:
    """Information about a GitLab project."""
    id: int
    name: str
    name_with_namespace: str
    description: str
    web_url: str
    ssh_url_to_repo: str
    http_url_to_repo: str
    namespace: Dict[str, Any]
    default_branch: str
    visibility: str
    archived: bool
    created_at: str
    last_activity_at: str
    star_count: int
    forks_count: int
    open_issues_count: int
    topics: List[str]
    
@dataclass
class MergeRequestInfo:
    """Information about a merge request."""
    id: int
    iid: int
    title: str
    description: str
    state: str
    created_at: str
    updated_at: str
    source_branch: str
    target_branch: str
    author: Dict[str, Any]
    assignee: Optional[Dict[str, Any]]
    reviewers: List[Dict[str, Any]]
    upvotes: int
    downvotes: int
    web_url: str
    has_conflicts: bool
    merge_status: str
    user_notes_count: int
    changes_count: str
    
@dataclass
class IssueInfo:
    """Information about an issue."""
    id: int
    iid: int
    title: str
    description: str
    state: str
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    author: Dict[str, Any]
    assignees: List[Dict[str, Any]]
    labels: List[str]
    milestone: Optional[Dict[str, Any]]
    web_url: str
    upvotes: int
    downvotes: int
    user_notes_count: int
    confidential: bool
    
@dataclass
class PipelineInfo:
    """Information about a pipeline."""
    id: int
    iid: int
    project_id: int
    status: str
    source: str
    ref: str
    sha: str
    web_url: str
    created_at: str
    updated_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    duration: Optional[int]
    variables: List[Dict[str, Any]]
    
@dataclass
class BranchInfo:
    """Information about a branch."""
    name: str
    merged: bool
    protected: bool
    default: bool
    developers_can_push: bool
    developers_can_merge: bool
    commit: Dict[str, Any]
    web_url: str
    
@dataclass
class CommitInfo:
    """Information about a commit."""
    id: str
    short_id: str
    title: str
    message: str
    author_name: str
    author_email: str
    authored_date: str
    committer_name: str
    committer_email: str
    committed_date: str
    created_at: str
    web_url: str
    stats: Dict[str, Any]
    
@dataclass
class FileInfo:
    """Information about a file."""
    id: str
    name: str
    type: str
    path: str
    mode: str
    content: Optional[str]
    encoding: Optional[str]
    size: int
    last_commit_id: str
    web_url: str

class GitLabMCPServer(BaseMCPServer):
    """GitLab MCP Server for GitLab platform operations."""
    
    def __init__(
        self,
        url: str = "https://gitlab.com",
        private_token: Optional[str] = None,
        oauth_token: Optional[str] = None,
        job_token: Optional[str] = None,
        ssl_verify: bool = True,
        timeout: int = 60,
        per_page: int = 100,
        pagination: str = "keyset",
        order_by: str = "created_at",
        sort: str = "desc",
        host: str = "127.0.0.1",
        port: int = 8004,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize GitLab MCP Server.
        
        Args:
            url: GitLab instance URL (default: https://gitlab.com)
            private_token: Private access token
            oauth_token: OAuth2 token
            job_token: CI job token
            ssl_verify: Verify SSL certificates
            timeout: Request timeout in seconds
            per_page: Items per page for pagination
            pagination: Pagination method
            order_by: Order results by field
            sort: Sort direction (asc/desc)
            host: Host to run MCP server on
            port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        # Initialize GitLab client
        try:
            # Determine authentication method
            auth_config = {}
            if private_token:
                auth_config['private_token'] = private_token
            elif oauth_token:
                auth_config['oauth_token'] = oauth_token
            elif job_token:
                auth_config['job_token'] = job_token
            else:
                # Try to get token from environment
                import os
                token = os.environ.get('GITLAB_PRIVATE_TOKEN') or \
                       os.environ.get('GITLAB_OAUTH_TOKEN') or \
                       os.environ.get('CI_JOB_TOKEN')
                if token:
                    auth_config['private_token'] = token
            
            self.gitlab_client = gitlab.Gitlab(
                url=url,
                **auth_config,
                ssl_verify=ssl_verify,
                timeout=timeout,
                per_page=per_page,
                pagination=pagination,
                order_by=order_by,
                sort=sort
            )
            
            # Test authentication
            self.gitlab_client.auth()
            self.connected = True
            
        except Exception as e:
            self.connected = False
            self.gitlab_client = None
            if debug:
                print(f"GitLab connection failed: {e}")
        
        # Initialize base class
        super().__init__(
            name="GitLab MCP Server",
            description="MCP server for GitLab platform operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _check_connection(self) -> bool:
        """Check GitLab connection."""
        if not self.connected or not self.gitlab_client:
            return False
        try:
            # Simple API call to verify connection
            self.gitlab_client.version()
            return True
        except Exception:
            self.connected = False
            return False
    
    def _parse_project(self, project) -> ProjectInfo:
        """Parse GitLab project object."""
        return ProjectInfo(
            id=project.id,
            name=project.name,
            name_with_namespace=project.name_with_namespace,
            description=project.description or "",
            web_url=project.web_url,
            ssh_url_to_repo=project.ssh_url_to_repo,
            http_url_to_repo=project.http_url_to_repo,
            namespace={
                "id": project.namespace['id'],
                "name": project.namespace['name'],
                "path": project.namespace['path'],
                "kind": project.namespace['kind'],
                "full_path": project.namespace['full_path']
            } if project.namespace else {},
            default_branch=project.default_branch,
            visibility=project.visibility,
            archived=project.archived,
            created_at=project.created_at,
            last_activity_at=project.last_activity_at,
            star_count=project.star_count,
            forks_count=project.forks_count,
            open_issues_count=project.open_issues_count,
            topics=project.topics or []
        )
    
    def _parse_merge_request(self, mr) -> MergeRequestInfo:
        """Parse GitLab merge request object."""
        return MergeRequestInfo(
            id=mr.id,
            iid=mr.iid,
            title=mr.title,
            description=mr.description or "",
            state=mr.state,
            created_at=mr.created_at,
            updated_at=mr.updated_at,
            source_branch=mr.source_branch,
            target_branch=mr.target_branch,
            author={
                "id": mr.author['id'],
                "name": mr.author['name'],
                "username": mr.author['username'],
                "avatar_url": mr.author.get('avatar_url')
            } if mr.author else {},
            assignee={
                "id": mr.assignee['id'],
                "name": mr.assignee['name'],
                "username": mr.assignee['username']
            } if mr.assignee else None,
            reviewers=[{
                "id": r['id'],
                "name": r['name'],
                "username": r['username']
            } for r in (mr.reviewers or [])],
            upvotes=mr.upvotes,
            downvotes=mr.downvotes,
            web_url=mr.web_url,
            has_conflicts=mr.has_conflicts,
            merge_status=mr.merge_status,
            user_notes_count=mr.user_notes_count,
            changes_count=mr.changes_count
        )
    
    def _parse_issue(self, issue) -> IssueInfo:
        """Parse GitLab issue object."""
        return IssueInfo(
            id=issue.id,
            iid=issue.iid,
            title=issue.title,
            description=issue.description or "",
            state=issue.state,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            closed_at=issue.closed_at,
            author={
                "id": issue.author['id'],
                "name": issue.author['name'],
                "username": issue.author['username']
            } if issue.author else {},
            assignees=[{
                "id": a['id'],
                "name": a['name'],
                "username": a['username']
            } for a in (issue.assignees or [])],
            labels=issue.labels,
            milestone={
                "id": issue.milestone['id'],
                "title": issue.milestone['title'],
                "description": issue.milestone['description']
            } if issue.milestone else None,
            web_url=issue.web_url,
            upvotes=issue.upvotes,
            downvotes=issue.downvotes,
            user_notes_count=issue.user_notes_count,
            confidential=issue.confidential
        )
    
    def _register_tools(self) -> None:
        """Register all GitLab-related tools."""
        self._register_project_tools()
        self._register_merge_request_tools()
        self._register_issue_tools()
        self._register_repository_tools()
        self._register_pipeline_tools()
        self._register_user_group_tools()
    
    def _register_project_tools(self):
        """Register project management tools."""
        
        @self.mcp_server.tool()
        def list_projects(
            owned: bool = True,
            starred: bool = False,
            visibility: Optional[str] = None,
            search: Optional[str] = None,
            order_by: str = "last_activity_at",
            sort: str = "desc",
            archived: bool = False
        ) -> Dict[str, Any]:
            """List GitLab projects.
            
            Args:
                owned: Show only projects owned by current user
                starred: Show only starred projects
                visibility: Filter by visibility (public, internal, private)
                search: Search projects by name
                order_by: Order by field (id, name, path, created_at, updated_at, last_activity_at)
                sort: Sort direction (asc, desc)
                archived: Include archived projects
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                # Build parameters
                params = {
                    "owned": owned,
                    "starred": starred,
                    "order_by": order_by,
                    "sort": sort,
                    "archived": archived
                }
                
                if visibility:
                    params["visibility"] = visibility
                if search:
                    params["search"] = search
                
                # Get projects
                projects = self.gitlab_client.projects.list(**params)
                
                project_list = []
                for project in projects:
                    try:
                        project_info = self._parse_project(project)
                        project_list.append(asdict(project_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing project {project.id}: {e}")
                        continue
                
                return {
                    "count": len(project_list),
                    "projects": project_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_project(project_id: Union[int, str]) -> Dict[str, Any]:
            """Get detailed information about a specific project.
            
            Args:
                project_id: Project ID or path (e.g., 'username/projectname')
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                project_info = self._parse_project(project)
                
                return {
                    "project": asdict(project_info)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_project(
            name: str,
            path: Optional[str] = None,
            namespace_id: Optional[int] = None,
            description: Optional[str] = None,
            visibility: str = "private",
            initialize_with_readme: bool = True,
            default_branch: str = "main"
        ) -> Dict[str, Any]:
            """Create a new GitLab project.
            
            Args:
                name: Project name
                path: Project path/slug (defaults to name)
                namespace_id: Namespace/group ID
                description: Project description
                visibility: Visibility level (private, internal, public)
                initialize_with_readme: Initialize with README.md
                default_branch: Default branch name
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.create({
                    'name': name,
                    'path': path or name.lower().replace(' ', '-'),
                    'namespace_id': namespace_id,
                    'description': description,
                    'visibility': visibility,
                    'initialize_with_readme': initialize_with_readme,
                    'default_branch': default_branch
                })
                
                project_info = self._parse_project(project)
                
                return {
                    "success": True,
                    "project": asdict(project_info),
                    "message": f"Project '{name}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def fork_project(
            project_id: Union[int, str],
            name: Optional[str] = None,
            path: Optional[str] = None,
            namespace_id: Optional[int] = None,
            visibility: Optional[str] = None
        ) -> Dict[str, Any]:
            """Fork an existing project."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                # Fork the project
                fork_data = {}
                if name:
                    fork_data['name'] = name
                if path:
                    fork_data['path'] = path
                if namespace_id:
                    fork_data['namespace_id'] = namespace_id
                if visibility:
                    fork_data['visibility'] = visibility
                
                fork = project.forks.create(fork_data)
                fork_info = self._parse_project(fork)
                
                return {
                    "success": True,
                    "fork": asdict(fork_info),
                    "message": f"Project forked successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_merge_request_tools(self):
        """Register merge request tools."""
        
        @self.mcp_server.tool()
        def list_merge_requests(
            project_id: Union[int, str],
            state: str = "opened",
            author_id: Optional[int] = None,
            assignee_id: Optional[int] = None,
            reviewer_id: Optional[int] = None,
            search: Optional[str] = None,
            order_by: str = "created_at",
            sort: str = "desc"
        ) -> Dict[str, Any]:
            """List merge requests for a project.
            
            Args:
                project_id: Project ID or path
                state: Merge request state (opened, closed, locked, merged, all)
                author_id: Filter by author ID
                assignee_id: Filter by assignee ID
                reviewer_id: Filter by reviewer ID
                search: Search in title and description
                order_by: Order by field
                sort: Sort direction
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                # Build parameters
                params = {
                    "state": state,
                    "order_by": order_by,
                    "sort": sort
                }
                
                if author_id:
                    params["author_id"] = author_id
                if assignee_id:
                    params["assignee_id"] = assignee_id
                if reviewer_id:
                    params["reviewer_id"] = reviewer_id
                if search:
                    params["search"] = search
                
                mrs = project.mergerequests.list(**params)
                
                mr_list = []
                for mr in mrs:
                    try:
                        mr_info = self._parse_merge_request(mr)
                        mr_list.append(asdict(mr_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing MR {mr.id}: {e}")
                        continue
                
                return {
                    "project_id": project_id,
                    "count": len(mr_list),
                    "merge_requests": mr_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_merge_request(
            project_id: Union[int, str],
            source_branch: str,
            target_branch: str,
            title: str,
            description: Optional[str] = None,
            assignee_id: Optional[int] = None,
            reviewer_ids: Optional[List[int]] = None,
            remove_source_branch: bool = True,
            squash: bool = False,
            labels: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """Create a new merge request.
            
            Args:
                project_id: Project ID or path
                source_branch: Source branch name
                target_branch: Target branch name
                title: Merge request title
                description: Detailed description
                assignee_id: Assignee user ID
                reviewer_ids: List of reviewer user IDs
                remove_source_branch: Remove source branch after merge
                squash: Squash commits into single commit
                labels: Labels to apply
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                # Create merge request
                mr_data = {
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "title": title,
                    "remove_source_branch": remove_source_branch,
                    "squash": squash
                }
                
                if description:
                    mr_data["description"] = description
                if assignee_id:
                    mr_data["assignee_id"] = assignee_id
                if reviewer_ids:
                    mr_data["reviewer_ids"] = reviewer_ids
                if labels:
                    mr_data["labels"] = ",".join(labels)
                
                mr = project.mergerequests.create(mr_data)
                mr_info = self._parse_merge_request(mr)
                
                return {
                    "success": True,
                    "merge_request": asdict(mr_info),
                    "message": f"Merge request '{title}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def merge_request_approve(
            project_id: Union[int, str],
            merge_request_iid: int
        ) -> Dict[str, Any]:
            """Approve a merge request."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                mr = project.mergerequests.get(merge_request_iid)
                
                mr.approve()
                
                return {
                    "success": True,
                    "merge_request_iid": merge_request_iid,
                    "message": f"Merge request #{merge_request_iid} approved"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def merge_merge_request(
            project_id: Union[int, str],
            merge_request_iid: int,
            merge_commit_message: Optional[str] = None,
            squash_commit_message: Optional[str] = None,
            should_remove_source_branch: Optional[bool] = None
        ) -> Dict[str, Any]:
            """Merge a merge request."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                mr = project.mergerequests.get(merge_request_iid)
                
                mr.merge(
                    merge_commit_message=merge_commit_message,
                    squash_commit_message=squash_commit_message,
                    should_remove_source_branch=should_remove_source_branch
                )
                
                return {
                    "success": True,
                    "merge_request_iid": merge_request_iid,
                    "message": f"Merge request #{merge_request_iid} merged successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_issue_tools(self):
        """Register issue management tools."""
        
        @self.mcp_server.tool()
        def list_issues(
            project_id: Optional[Union[int, str]] = None,
            state: str = "opened",
            labels: Optional[List[str]] = None,
            assignee_id: Optional[int] = None,
            author_id: Optional[int] = None,
            milestone: Optional[str] = None,
            search: Optional[str] = None,
            order_by: str = "created_at",
            sort: str = "desc"
        ) -> Dict[str, Any]:
            """List issues.
            
            Args:
                project_id: Filter by project (None for all projects)
                state: Issue state (opened, closed, all)
                labels: Filter by labels
                assignee_id: Filter by assignee
                author_id: Filter by author
                milestone: Filter by milestone
                search: Search in title and description
                order_by: Order by field
                sort: Sort direction
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                if project_id:
                    # Get issues for specific project
                    project = self.gitlab_client.projects.get(project_id)
                    issues = project.issues
                else:
                    # Get issues across all projects
                    issues = self.gitlab_client.issues
                
                # Build parameters
                params = {
                    "state": state,
                    "order_by": order_by,
                    "sort": sort
                }
                
                if labels:
                    params["labels"] = labels
                if assignee_id:
                    params["assignee_id"] = assignee_id
                if author_id:
                    params["author_id"] = author_id
                if milestone:
                    params["milestone"] = milestone
                if search:
                    params["search"] = search
                
                issue_list = []
                for issue in issues.list(**params):
                    try:
                        issue_info = self._parse_issue(issue)
                        issue_list.append(asdict(issue_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing issue {issue.id}: {e}")
                        continue
                
                return {
                    "project_id": project_id or "all",
                    "count": len(issue_list),
                    "issues": issue_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_issue(
            project_id: Union[int, str],
            title: str,
            description: Optional[str] = None,
            assignee_ids: Optional[List[int]] = None,
            labels: Optional[List[str]] = None,
            milestone_id: Optional[int] = None,
            confidential: bool = False
        ) -> Dict[str, Any]:
            """Create a new issue.
            
            Args:
                project_id: Project ID or path
                title: Issue title
                description: Issue description
                assignee_ids: List of assignee user IDs
                labels: Labels to apply
                milestone_id: Milestone ID
                confidential: Make issue confidential
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                issue_data = {
                    "title": title,
                    "confidential": confidential
                }
                
                if description:
                    issue_data["description"] = description
                if assignee_ids:
                    issue_data["assignee_ids"] = assignee_ids
                if labels:
                    issue_data["labels"] = ",".join(labels)
                if milestone_id:
                    issue_data["milestone_id"] = milestone_id
                
                issue = project.issues.create(issue_data)
                issue_info = self._parse_issue(issue)
                
                return {
                    "success": True,
                    "issue": asdict(issue_info),
                    "message": f"Issue '{title}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_repository_tools(self):
        """Register repository tools."""
        
        @self.mcp_server.tool()
        def list_branches(
            project_id: Union[int, str],
            search: Optional[str] = None
        ) -> Dict[str, Any]:
            """List branches in a repository."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                branches = project.branches.list(search=search)
                
                branch_list = []
                for branch in branches:
                    branch_info = BranchInfo(
                        name=branch.name,
                        merged=branch.merged,
                        protected=branch.protected,
                        default=branch.default,
                        developers_can_push=branch.developers_can_push,
                        developers_can_merge=branch.developers_can_merge,
                        commit={
                            "id": branch.commit['id'],
                            "title": branch.commit['title'],
                            "message": branch.commit['message'],
                            "author_name": branch.commit['author_name'],
                            "author_email": branch.commit['author_email']
                        } if branch.commit else {},
                        web_url=f"{project.web_url}/-/tree/{branch.name}"
                    )
                    branch_list.append(asdict(branch_info))
                
                return {
                    "project_id": project_id,
                    "count": len(branch_list),
                    "branches": branch_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_branch(
            project_id: Union[int, str],
            branch_name: str,
            ref: str
        ) -> Dict[str, Any]:
            """Create a new branch.
            
            Args:
                project_id: Project ID or path
                branch_name: New branch name
                ref: Source branch/tag/commit
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                branch = project.branches.create({'branch': branch_name, 'ref': ref})
                
                return {
                    "success": True,
                    "branch": branch.name,
                    "ref": ref,
                    "message": f"Branch '{branch_name}' created from '{ref}'"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_file(
            project_id: Union[int, str],
            file_path: str,
            ref: str = "main"
        ) -> Dict[str, Any]:
            """Get file content from repository.
            
            Args:
                project_id: Project ID or path
                file_path: Path to file in repository
                ref: Branch, tag, or commit
            """
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                # Get file content
                try:
                    file_content = project.files.get(file_path=file_path, ref=ref)
                    
                    # Decode content if needed
                    content = file_content.content
                    if file_content.encoding == 'base64':
                        content = base64.b64decode(content).decode('utf-8')
                    
                    file_info = FileInfo(
                        id=file_content.id,
                        name=Path(file_path).name,
                        type="blob",
                        path=file_path,
                        mode=file_content.mode,
                        content=content,
                        encoding=file_content.encoding,
                        size=file_content.size,
                        last_commit_id=file_content.last_commit_id,
                        web_url=f"{project.web_url}/-/blob/{ref}/{file_path}"
                    )
                    
                    return {
                        "file": asdict(file_info),
                        "ref": ref
                    }
                except Exception as e:
                    # Try to list directory if file not found
                    dir_content = []
                    try:
                        # This might be a directory, try to list it
                        repo_tree = project.repository_tree(path=file_path, ref=ref)
                        for item in repo_tree:
                            dir_content.append({
                                "name": item['name'],
                                "type": item['type'],
                                "path": item['path'],
                                "mode": item.get('mode', '')
                            })
                        
                        return {
                            "is_directory": True,
                            "path": file_path,
                            "ref": ref,
                            "contents": dir_content
                        }
                    except:
                        return {"error": f"File or directory not found: {file_path}"}
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_file(
            project_id: Union[int, str],
            file_path: str,
            content: str,
            branch: str = "main",
            commit_message: Optional[str] = None,
            author_email: Optional[str] = None,
            author_name: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new file in repository."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                if not commit_message:
                    commit_message = f"Add {file_path}"
                
                file_data = {
                    'file_path': file_path,
                    'branch': branch,
                    'content': content,
                    'commit_message': commit_message
                }
                
                if author_email:
                    file_data['author_email'] = author_email
                if author_name:
                    file_data['author_name'] = author_name
                
                file = project.files.create(file_data)
                
                return {
                    "success": True,
                    "file_path": file_path,
                    "branch": branch,
                    "commit_id": file.commit_id,
                    "message": f"File '{file_path}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_pipeline_tools(self):
        """Register pipeline tools."""
        
        @self.mcp_server.tool()
        def list_pipelines(
            project_id: Union[int, str],
            status: Optional[str] = None,
            ref: Optional[str] = None,
            sha: Optional[str] = None,
            scope: str = "all",
            order_by: str = "id",
            sort: str = "desc"
        ) -> Dict[str, Any]:
            """List CI/CD pipelines for a project."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                params = {
                    "scope": scope,
                    "order_by": order_by,
                    "sort": sort
                }
                
                if status:
                    params["status"] = status
                if ref:
                    params["ref"] = ref
                if sha:
                    params["sha"] = sha
                
                pipelines = project.pipelines.list(**params)
                
                pipeline_list = []
                for pipeline in pipelines:
                    pipeline_info = PipelineInfo(
                        id=pipeline.id,
                        iid=pipeline.iid,
                        project_id=pipeline.project_id,
                        status=pipeline.status,
                        source=pipeline.source,
                        ref=pipeline.ref,
                        sha=pipeline.sha,
                        web_url=pipeline.web_url,
                        created_at=pipeline.created_at,
                        updated_at=pipeline.updated_at,
                        started_at=pipeline.started_at,
                        finished_at=pipeline.finished_at,
                        duration=pipeline.duration,
                        variables=pipeline.variables if hasattr(pipeline, 'variables') else []
                    )
                    pipeline_list.append(asdict(pipeline_info))
                
                return {
                    "project_id": project_id,
                    "count": len(pipeline_list),
                    "pipelines": pipeline_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def run_pipeline(
            project_id: Union[int, str],
            ref: str,
            variables: Optional[Dict[str, str]] = None
        ) -> Dict[str, Any]:
            """Trigger a new pipeline."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                project = self.gitlab_client.projects.get(project_id)
                
                pipeline_data = {
                    "ref": ref
                }
                
                if variables:
                    pipeline_data["variables"] = [
                        {"key": k, "value": v} for k, v in variables.items()
                    ]
                
                pipeline = project.pipelines.create(pipeline_data)
                
                return {
                    "success": True,
                    "pipeline_id": pipeline.id,
                    "ref": ref,
                    "web_url": pipeline.web_url,
                    "message": f"Pipeline triggered for ref '{ref}'"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_user_group_tools(self):
        """Register user and group tools."""
        
        @self.mcp_server.tool()
        def get_current_user() -> Dict[str, Any]:
            """Get information about the authenticated user."""
            if not self._check_connection():
                return {"error": "GitLab connection not available"}
            
            try:
                user = self.gitlab_client.user
                return {
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "name": user.name,
                        "email": user.email,
                        "avatar_url": user.avatar_url,
                        "web_url": user.web_url,
                        "created_at": user.created_at,
                        "is_admin": user.is_admin,
                        "bio": user.bio,
                        "location": user.location,
                        "public_email": user.public_email,
                        "skype": user.skype,
                        "linkedin": user.linkedin,
                        "twitter": user.twitter,
                        "website_url": user.website_url,
                        "organization": user.organization
                    }
                }
            except Exception as e:
                return {"error": str(e)}


# CLI interface
if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="GitLab MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="MCP server host")
    parser.add_argument("--port", type=int, default=8004, help="MCP server port")
    parser.add_argument("--gitlab-url", default="https://gitlab.com", help="GitLab instance URL")
    parser.add_argument("--private-token", help="GitLab private token")
    parser.add_argument("--transport", default="stdio", 
                       choices=['stdio', 'sse', 'streamable-http'],
                       help="Transport type")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Get token from environment if not provided
    token = args.private_token or os.environ.get('GITLAB_PRIVATE_TOKEN')
    
    server = GitLabMCPServer(
        url=args.gitlab_url,
        private_token=token,
        host=args.host,
        port=args.port,
        transport=args.transport,
        debug=args.debug
    )
    
    print(f"Starting GitLab MCP Server on {args.host}:{args.port}")
    print(f"GitLab URL: {args.gitlab_url}")
    print(f"Transport: {args.transport}")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down GitLab MCP Server...")
    except Exception as e:
        print(f"Error: {e}")