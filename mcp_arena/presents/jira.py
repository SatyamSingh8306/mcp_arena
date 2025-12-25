from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
from atlassian import Jira
import json
from enum import Enum
from mcp_arena.mcp.server import BaseMCPServer

class IssueStatus(Enum):
    """Issue status enumeration."""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    BACKLOG = "Backlog"
    SELECTED = "Selected for Development"
    
class IssueType(Enum):
    """Issue type enumeration."""
    BUG = "Bug"
    TASK = "Task"
    STORY = "Story"
    EPIC = "Epic"
    SUBTASK = "Sub-task"
    
class Priority(Enum):
    """Priority enumeration."""
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"

@dataclass
class ProjectInfo:
    """Information about a Jira project."""
    id: str
    key: str
    name: str
    project_type: str
    style: str
    simplified: bool
    avatar_urls: Dict[str, str]
    lead: Dict[str, Any]
    components: List[Dict[str, Any]]
    issue_types: List[Dict[str, Any]]
    url: str
    
@dataclass
class IssueInfo:
    """Information about a Jira issue."""
    id: str
    key: str
    summary: str
    description: str
    status: str
    issue_type: str
    priority: str
    assignee: Optional[Dict[str, Any]]
    reporter: Optional[Dict[str, Any]]
    created: str
    updated: str
    due_date: Optional[str]
    resolution: Optional[str]
    labels: List[str]
    components: List[Dict[str, Any]]
    fix_versions: List[Dict[str, Any]]
    affected_versions: List[Dict[str, Any]]
    project: Dict[str, Any]
    time_estimates: Dict[str, Any]
    time_tracking: Dict[str, Any]
    custom_fields: Dict[str, Any]
    
@dataclass
class SprintInfo:
    """Information about a Jira sprint."""
    id: int
    name: str
    state: str
    start_date: Optional[str]
    end_date: Optional[str]
    complete_date: Optional[str]
    origin_board_id: int
    goal: Optional[str]
    
@dataclass
class BoardInfo:
    """Information about a Jira board."""
    id: int
    name: str
    type: str
    filter_id: int
    location: Dict[str, Any]
    
@dataclass
class UserInfo:
    """Information about a Jira user."""
    account_id: str
    account_type: str
    email_address: Optional[str]
    display_name: str
    active: bool
    time_zone: str
    avatar_urls: Dict[str, str]
    
@dataclass
class CommentInfo:
    """Information about a Jira comment."""
    id: str
    author: Dict[str, Any]
    body: str
    created: str
    updated: str
    visibility: Optional[Dict[str, Any]]
    
@dataclass
class WorklogInfo:
    """Information about worklog entry."""
    id: str
    author: Dict[str, Any]
    time_spent: str
    time_spent_seconds: int
    started: str
    comment: str
    created: str
    updated: str
    
@dataclass
class TransitionInfo:
    """Information about issue transition."""
    id: str
    name: str
    to: Dict[str, Any]
    has_screen: bool
    is_global: bool
    is_initial: bool
    is_available: bool
    is_conditional: bool

class JiraMCPServer(BaseMCPServer):
    """Jira MCP Server for Atlassian Jira operations."""
    
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        cloud: bool = True,
        timeout: int = 60,
        verify_ssl: bool = True,
        advanced_mode: bool = False,
        host: str = "127.0.0.1",
        port: int = 8007,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Jira MCP Server.
        
        Args:
            url: Jira instance URL
            username: Jira username
            password: Jira password or API token
            cloud: Use Jira Cloud (True) or Server/Data Center (False)
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
            advanced_mode: Enable advanced mode for complex queries
            host: Host to run MCP server on
            port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        try:
            self.jira_client = Jira(
                url=url,
                username=username,
                password=password,
                cloud=cloud,
                timeout=timeout,
                verify_ssl=verify_ssl,
                advanced_mode=advanced_mode
            )
            
            # Test connection
            self.jira_client.get_server_info()
            self.connected = True
            self.is_cloud = cloud
            
        except Exception as e:
            self.connected = False
            self.jira_client = None
            if debug:
                print(f"Jira connection failed: {e}")
        
        # Initialize base class
        super().__init__(
            name="Jira MCP Server",
            description="MCP server for Atlassian Jira operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _check_connection(self) -> bool:
        """Check Jira connection."""
        if not self.connected or not self.jira_client:
            return False
        try:
            self.jira_client.get_server_info()
            return True
        except Exception:
            self.connected = False
            return False
    
    def _parse_project(self, project) -> ProjectInfo:
        """Parse Jira project object."""
        return ProjectInfo(
            id=project.get('id', ''),
            key=project.get('key', ''),
            name=project.get('name', ''),
            project_type=project.get('projectTypeKey', ''),
            style=project.get('style', 'classic'),
            simplified=project.get('simplified', False),
            avatar_urls=project.get('avatarUrls', {}),
            lead=project.get('lead', {}),
            components=project.get('components', []),
            issue_types=project.get('issueTypes', []),
            url=project.get('self', '')
        )
    
    def _parse_issue(self, issue) -> IssueInfo:
        """Parse Jira issue object."""
        fields = issue.get('fields', {})
        
        # Extract custom fields
        custom_fields = {}
        for key, value in fields.items():
            if key.startswith('customfield_'):
                custom_fields[key] = value
        
        return IssueInfo(
            id=issue.get('id', ''),
            key=issue.get('key', ''),
            summary=fields.get('summary', ''),
            description=fields.get('description', ''),
            status=fields.get('status', {}).get('name', '') if fields.get('status') else '',
            issue_type=fields.get('issuetype', {}).get('name', '') if fields.get('issuetype') else '',
            priority=fields.get('priority', {}).get('name', '') if fields.get('priority') else '',
            assignee=fields.get('assignee', {}),
            reporter=fields.get('reporter', {}),
            created=fields.get('created', ''),
            updated=fields.get('updated', ''),
            due_date=fields.get('duedate'),
            resolution=fields.get('resolution', {}).get('name', '') if fields.get('resolution') else '',
            labels=fields.get('labels', []),
            components=fields.get('components', []),
            fix_versions=fields.get('fixVersions', []),
            affected_versions=fields.get('versions', []),
            project=fields.get('project', {}),
            time_estimates={
                'original_estimate': fields.get('timeoriginalestimate'),
                'remaining_estimate': fields.get('timeestimate'),
                'time_spent': fields.get('timespent')
            },
            time_tracking=fields.get('timetracking', {}),
            custom_fields=custom_fields
        )
    
    def _register_tools(self) -> None:
        """Register all Jira-related tools."""
        self._register_project_tools()
        self._register_issue_tools()
        self._register_sprint_tools()
        self._register_board_tools()
        self._register_user_tools()
        self._register_search_tools()
        self._register_workflow_tools()
    
    def _register_project_tools(self):
        """Register project management tools."""
        
        @self.mcp_server.tool()
        def list_projects() -> Dict[str, Any]:
            """List Jira projects."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                projects = self.jira_client.projects()
                
                project_list = []
                for project in projects:
                    try:
                        project_info = self._parse_project(project)
                        project_list.append(asdict(project_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing project {project.get('key')}: {e}")
                        continue
                
                return {
                    "count": len(project_list),
                    "projects": project_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_project(project_key: str) -> Dict[str, Any]:
            """Get detailed information about a project."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                project = self.jira_client.project(project_key)
                project_info = self._parse_project(project)
                
                return {
                    "project": asdict(project_info)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_project_components(project_key: str) -> Dict[str, Any]:
            """Get components for a project."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                components = self.jira_client.get_project_components(project_key)
                
                return {
                    "project": project_key,
                    "count": len(components),
                    "components": components
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_project_versions(project_key: str) -> Dict[str, Any]:
            """Get versions for a project."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                versions = self.jira_client.get_project_versions(project_key)
                
                return {
                    "project": project_key,
                    "count": len(versions),
                    "versions": versions
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_issue_tools(self):
        """Register issue management tools."""
        
        @self.mcp_server.tool()
        def get_issue(issue_key: str) -> Dict[str, Any]:
            """Get detailed information about an issue."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                issue = self.jira_client.issue(issue_key)
                issue_info = self._parse_issue(issue)
                
                return {
                    "issue": asdict(issue_info)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_issue(
            project_key: str,
            summary: str,
            issue_type: str,
            description: Optional[str] = None,
            priority: Optional[str] = None,
            assignee: Optional[str] = None,
            labels: Optional[List[str]] = None,
            components: Optional[List[str]] = None,
            due_date: Optional[str] = None,
            parent_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new Jira issue.
            
            Args:
                project_key: Project key
                summary: Issue summary/title
                issue_type: Issue type (Bug, Task, Story, etc.)
                description: Issue description
                priority: Priority level
                assignee: Assignee username or account ID
                labels: List of labels
                components: List of component names
                due_date: Due date (YYYY-MM-DD)
                parent_key: Parent issue key (for sub-tasks)
            """
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                # Build issue data
                issue_data = {
                    'project': {'key': project_key},
                    'summary': summary,
                    'issuetype': {'name': issue_type}
                }
                
                if description:
                    issue_data['description'] = description
                if priority:
                    issue_data['priority'] = {'name': priority}
                if assignee:
                    if self.is_cloud:
                        issue_data['assignee'] = {'id': assignee}
                    else:
                        issue_data['assignee'] = {'name': assignee}
                if labels:
                    issue_data['labels'] = labels
                if components:
                    issue_data['components'] = [{'name': c} for c in components]
                if due_date:
                    issue_data['duedate'] = due_date
                if parent_key:
                    issue_data['parent'] = {'key': parent_key}
                
                # Create issue
                issue = self.jira_client.create_issue(fields=issue_data)
                
                # Get created issue with full details
                created_issue = self.jira_client.issue(issue['key'])
                issue_info = self._parse_issue(created_issue)
                
                return {
                    "success": True,
                    "issue": asdict(issue_info),
                    "message": f"Issue '{issue['key']}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def update_issue(
            issue_key: str,
            summary: Optional[str] = None,
            description: Optional[str] = None,
            priority: Optional[str] = None,
            assignee: Optional[str] = None,
            labels: Optional[List[str]] = None,
            due_date: Optional[str] = None,
            add_labels: Optional[List[str]] = None,
            remove_labels: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """Update an existing issue."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                update_data = {}
                
                if summary is not None:
                    update_data['summary'] = [{'set': summary}]
                if description is not None:
                    update_data['description'] = [{'set': description}]
                if priority is not None:
                    update_data['priority'] = [{'set': {'name': priority}}]
                if assignee is not None:
                    if self.is_cloud:
                        update_data['assignee'] = [{'set': {'id': assignee}}]
                    else:
                        update_data['assignee'] = [{'set': {'name': assignee}}]
                if due_date is not None:
                    update_data['duedate'] = [{'set': due_date}]
                
                # Handle labels
                label_operations = []
                if labels is not None:
                    label_operations.append({'set': labels})
                if add_labels:
                    label_operations.append({'add': add_labels})
                if remove_labels:
                    label_operations.append({'remove': remove_labels})
                
                if label_operations:
                    update_data['labels'] = label_operations
                
                if not update_data:
                    return {"error": "No update data provided"}
                
                # Update issue
                self.jira_client.update_issue(issue_key, update_data)
                
                # Get updated issue
                updated_issue = self.jira_client.issue(issue_key)
                issue_info = self._parse_issue(updated_issue)
                
                return {
                    "success": True,
                    "issue": asdict(issue_info),
                    "message": f"Issue '{issue_key}' updated successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def delete_issue(issue_key: str) -> Dict[str, Any]:
            """Delete an issue."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                # Get issue info before deletion
                issue = self.jira_client.issue(issue_key)
                issue_summary = issue.get('fields', {}).get('summary', 'Unknown')
                
                # Delete issue
                self.jira_client.delete_issue(issue_key)
                
                return {
                    "success": True,
                    "issue_key": issue_key,
                    "summary": issue_summary,
                    "message": f"Issue '{issue_key}' deleted successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def add_comment(
            issue_key: str,
            comment: str,
            visibility: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add a comment to an issue."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                comment_data = {
                    'body': comment
                }
                
                if visibility:
                    comment_data['visibility'] = {
                        'type': 'role',
                        'value': visibility
                    }
                
                added_comment = self.jira_client.issue_add_comment(issue_key, comment_data)
                
                return {
                    "success": True,
                    "comment_id": added_comment['id'],
                    "issue_key": issue_key,
                    "message": "Comment added successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def list_comments(issue_key: str) -> Dict[str, Any]:
            """List comments on an issue."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                comments = self.jira_client.get_issue_comments(issue_key)
                
                comment_list = []
                for comment in comments.get('comments', []):
                    comment_info = CommentInfo(
                        id=comment.get('id', ''),
                        author=comment.get('author', {}),
                        body=comment.get('body', ''),
                        created=comment.get('created', ''),
                        updated=comment.get('updated', ''),
                        visibility=comment.get('visibility', {})
                    )
                    comment_list.append(asdict(comment_info))
                
                return {
                    "issue_key": issue_key,
                    "count": len(comment_list),
                    "comments": comment_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def add_worklog(
            issue_key: str,
            time_spent: str,
            started: Optional[str] = None,
            comment: Optional[str] = None,
            reduce_by: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add worklog entry to an issue.
            
            Args:
                issue_key: Issue key
                time_spent: Time spent (e.g., "2h 30m", "1d", "30m")
                started: Start time (ISO format, default: now)
                comment: Worklog comment
                reduce_by: Reduce remaining estimate by this amount
            """
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                worklog_data = {
                    'timeSpent': time_spent
                }
                
                if started:
                    worklog_data['started'] = started
                if comment:
                    worklog_data['comment'] = comment
                if reduce_by:
                    worklog_data['reduceBy'] = reduce_by
                
                worklog = self.jira_client.add_worklog(
                    issue=issue_key,
                    worklog=worklog_data
                )
                
                return {
                    "success": True,
                    "worklog_id": worklog['id'],
                    "time_spent": time_spent,
                    "message": "Worklog added successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def list_worklogs(issue_key: str) -> Dict[str, Any]:
            """List worklogs for an issue."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                worklogs = self.jira_client.get_issue_worklogs(issue_key)
                
                worklog_list = []
                for worklog in worklogs.get('worklogs', []):
                    worklog_info = WorklogInfo(
                        id=worklog.get('id', ''),
                        author=worklog.get('author', {}),
                        time_spent=worklog.get('timeSpent', ''),
                        time_spent_seconds=worklog.get('timeSpentSeconds', 0),
                        started=worklog.get('started', ''),
                        comment=worklog.get('comment', ''),
                        created=worklog.get('created', ''),
                        updated=worklog.get('updated', '')
                    )
                    worklog_list.append(asdict(worklog_info))
                
                return {
                    "issue_key": issue_key,
                    "count": len(worklog_list),
                    "total_time": sum(w.time_spent_seconds for w in worklog_list),
                    "worklogs": worklog_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_sprint_tools(self):
        """Register sprint management tools."""
        
        @self.mcp_server.tool()
        def list_sprints(board_id: int) -> Dict[str, Any]:
            """List sprints for a board."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                sprints = self.jira_client.get_all_sprint(board_id)
                
                sprint_list = []
                for sprint in sprints:
                    sprint_info = SprintInfo(
                        id=sprint.get('id', 0),
                        name=sprint.get('name', ''),
                        state=sprint.get('state', ''),
                        start_date=sprint.get('startDate'),
                        end_date=sprint.get('endDate'),
                        complete_date=sprint.get('completeDate'),
                        origin_board_id=sprint.get('originBoardId', 0),
                        goal=sprint.get('goal')
                    )
                    sprint_list.append(asdict(sprint_info))
                
                return {
                    "board_id": board_id,
                    "count": len(sprint_list),
                    "sprints": sprint_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_sprint(
            board_id: int,
            name: str,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            goal: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new sprint."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                sprint_data = {
                    'name': name,
                    'originBoardId': board_id
                }
                
                if start_date:
                    sprint_data['startDate'] = start_date
                if end_date:
                    sprint_data['endDate'] = end_date
                if goal:
                    sprint_data['goal'] = goal
                
                sprint = self.jira_client.create_sprint(**sprint_data)
                
                return {
                    "success": True,
                    "sprint_id": sprint['id'],
                    "name": name,
                    "message": f"Sprint '{name}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_sprint_issues(
            sprint_id: int,
            max_results: int = 100
        ) -> Dict[str, Any]:
            """Get issues in a sprint."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                issues = self.jira_client.get_sprint_issues(
                    sprint_id=sprint_id,
                    max_results=max_results
                )
                
                issue_list = []
                for issue in issues.get('issues', []):
                    try:
                        issue_info = self._parse_issue(issue)
                        issue_list.append(asdict(issue_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing issue {issue.get('key')}: {e}")
                        continue
                
                return {
                    "sprint_id": sprint_id,
                    "count": len(issue_list),
                    "issues": issue_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_board_tools(self):
        """Register board management tools."""
        
        @self.mcp_server.tool()
        def list_boards(
            board_type: Optional[str] = None,
            project_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """List Jira boards.
            
            Args:
                board_type: Board type (scrum, kanban)
                project_key: Filter by project key
            """
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                boards = self.jira_client.get_all_boards()
                
                board_list = []
                for board in boards.get('values', []):
                    # Apply filters
                    if board_type and board.get('type') != board_type:
                        continue
                    
                    if project_key:
                        location = board.get('location', {})
                        if location.get('projectKey') != project_key:
                            continue
                    
                    board_info = BoardInfo(
                        id=board.get('id', 0),
                        name=board.get('name', ''),
                        type=board.get('type', ''),
                        filter_id=board.get('filterId', 0),
                        location=board.get('location', {})
                    )
                    board_list.append(asdict(board_info))
                
                return {
                    "count": len(board_list),
                    "boards": board_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_user_tools(self):
        """Register user management tools."""
        
        @self.mcp_server.tool()
        def get_current_user() -> Dict[str, Any]:
            """Get information about the authenticated user."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                user = self.jira_client.myself()
                
                user_info = UserInfo(
                    account_id=user.get('accountId', ''),
                    account_type=user.get('accountType', ''),
                    email_address=user.get('emailAddress'),
                    display_name=user.get('displayName', ''),
                    active=user.get('active', False),
                    time_zone=user.get('timeZone', ''),
                    avatar_urls=user.get('avatarUrls', {})
                )
                
                return {
                    "user": asdict(user_info)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def search_users(
            query: str,
            max_results: int = 50
        ) -> Dict[str, Any]:
            """Search for users."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                users = self.jira_client.search_users(
                    query=query,
                    maxResults=max_results
                )
                
                user_list = []
                for user in users:
                    user_info = UserInfo(
                        account_id=user.get('accountId', ''),
                        account_type=user.get('accountType', ''),
                        email_address=user.get('emailAddress'),
                        display_name=user.get('displayName', ''),
                        active=user.get('active', False),
                        time_zone=user.get('timeZone', ''),
                        avatar_urls=user.get('avatarUrls', {})
                    )
                    user_list.append(asdict(user_info))
                
                return {
                    "query": query,
                    "count": len(user_list),
                    "users": user_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_search_tools(self):
        """Register search tools."""
        
        @self.mcp_server.tool()
        def search_issues(
            jql: str,
            max_results: int = 50,
            fields: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """Search for issues using JQL (Jira Query Language).
            
            Args:
                jql: JQL query string
                max_results: Maximum number of results
                fields: List of fields to include in response
            """
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                if fields is None:
                    fields = [
                        'summary', 'status', 'assignee', 'priority',
                        'issuetype', 'created', 'updated', 'description'
                    ]
                
                issues = self.jira_client.jql(
                    jql=jql,
                    limit=max_results,
                    fields=fields
                )
                
                issue_list = []
                for issue in issues.get('issues', []):
                    try:
                        issue_info = self._parse_issue(issue)
                        issue_list.append(asdict(issue_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing issue {issue.get('key')}: {e}")
                        continue
                
                return {
                    "jql": jql,
                    "total": issues.get('total', 0),
                    "count": len(issue_list),
                    "issues": issue_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def search_issues_simple(
            query: str,
            project_key: Optional[str] = None,
            assignee: Optional[str] = None,
            status: Optional[str] = None,
            issue_type: Optional[str] = None,
            max_results: int = 50
        ) -> Dict[str, Any]:
            """Simple issue search with common filters.
            
            Args:
                query: Search text
                project_key: Filter by project
                assignee: Filter by assignee
                status: Filter by status
                issue_type: Filter by issue type
                max_results: Maximum number of results
            """
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                # Build JQL query
                jql_parts = []
                
                if query:
                    jql_parts.append(f'(summary ~ "{query}" OR description ~ "{query}")')
                
                if project_key:
                    jql_parts.append(f'project = "{project_key}"')
                
                if assignee:
                    if self.is_cloud:
                        jql_parts.append(f'assignee = "{assignee}"')
                    else:
                        jql_parts.append(f'assignee = "{assignee}"')
                
                if status:
                    jql_parts.append(f'status = "{status}"')
                
                if issue_type:
                    jql_parts.append(f'issuetype = "{issue_type}"')
                
                jql = ' AND '.join(jql_parts) if jql_parts else 'ORDER BY created DESC'
                
                return search_issues(jql=jql, max_results=max_results)
            except Exception as e:
                return {"error": str(e)}
    
    def _register_workflow_tools(self):
        """Register workflow tools."""
        
        @self.mcp_server.tool()
        def get_transitions(issue_key: str) -> Dict[str, Any]:
            """Get available transitions for an issue."""
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                transitions = self.jira_client.get_issue_transitions(issue_key)
                
                transition_list = []
                for transition in transitions.get('transitions', []):
                    transition_info = TransitionInfo(
                        id=transition.get('id', ''),
                        name=transition.get('name', ''),
                        to=transition.get('to', {}),
                        has_screen=transition.get('hasScreen', False),
                        is_global=transition.get('isGlobal', False),
                        is_initial=transition.get('isInitial', False),
                        is_available=transition.get('isAvailable', True),
                        is_conditional=transition.get('isConditional', False)
                    )
                    transition_list.append(asdict(transition_info))
                
                return {
                    "issue_key": issue_key,
                    "count": len(transition_list),
                    "transitions": transition_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def transition_issue(
            issue_key: str,
            transition_id: str,
            comment: Optional[str] = None,
            resolution: Optional[str] = None
        ) -> Dict[str, Any]:
            """Transition an issue to a new status.
            
            Args:
                issue_key: Issue key
                transition_id: Transition ID
                comment: Optional comment for the transition
                resolution: Resolution (for closing issues)
            """
            if not self._check_connection():
                return {"error": "Jira connection not available"}
            
            try:
                transition_data = {
                    'transition': {'id': transition_id}
                }
                
                if comment or resolution:
                    transition_data['fields'] = {}
                    if comment:
                        transition_data['update'] = {
                            'comment': [{'add': {'body': comment}}]
                        }
                    if resolution:
                        transition_data['fields']['resolution'] = {'name': resolution}
                
                self.jira_client.issue_transition(issue_key, transition_data)
                
                # Get updated issue
                updated_issue = self.jira_client.issue(issue_key)
                issue_info = self._parse_issue(updated_issue)
                
                return {
                    "success": True,
                    "issue": asdict(issue_info),
                    "message": f"Issue '{issue_key}' transitioned successfully"
                }
            except Exception as e:
                return {"error": str(e)}


# CLI interface
if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Jira MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="MCP server host")
    parser.add_argument("--port", type=int, default=8007, help="MCP server port")
    parser.add_argument("--url", required=True, help="Jira instance URL")
    parser.add_argument("--username", help="Jira username")
    parser.add_argument("--password", help="Jira password or API token")
    parser.add_argument("--server", action="store_true", 
                       help="Use Jira Server (default: Cloud)")
    parser.add_argument("--transport", default="stdio", 
                       choices=['stdio', 'sse', 'streamable-http'],
                       help="Transport type")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Get credentials from environment if not provided
    username = args.username or os.environ.get('JIRA_USERNAME')
    password = args.password or os.environ.get('JIRA_PASSWORD')
    
    server = JiraMCPServer(
        url=args.url,
        username=username,
        password=password,
        cloud=not args.server,
        host=args.host,
        port=args.port,
        transport=args.transport,
        debug=args.debug
    )
    
    print(f"Starting Jira MCP Server on {args.host}:{args.port}")
    print(f"Jira URL: {args.url}")
    print(f"Mode: {'Server' if args.server else 'Cloud'}")
    print(f"Transport: {args.transport}")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down Jira MCP Server...")
    except Exception as e:
        print(f"Error: {e}")