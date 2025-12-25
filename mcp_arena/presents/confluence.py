from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
from atlassian import Confluence
import json
import html2text
from pathlib import Path
from enum import Enum
import re
from mcp_arena.mcp.server import BaseMCPServer

class ContentStatus(Enum):
    """Content status enumeration."""
    CURRENT = "current"
    DRAFT = "draft"
    ARCHIVED = "archived"
    DELETED = "deleted"

class ContentType(Enum):
    """Content type enumeration."""
    PAGE = "page"
    BLOGPOST = "blogpost"
    COMMENT = "comment"
    ATTACHMENT = "attachment"

@dataclass
class SpaceInfo:
    """Information about a Confluence space."""
    id: int
    key: str
    name: str
    type: str
    status: str
    description: Optional[str]
    homepage_id: Optional[int]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    
@dataclass
class PageInfo:
    """Information about a Confluence page."""
    id: str
    title: str
    type: str
    status: str
    space_key: str
    version: int
    created_by: Dict[str, Any]
    created_at: str
    updated_by: Dict[str, Any]
    updated_at: str
    body_html: str
    body_plain: str
    ancestors: List[Dict[str, Any]]
    children: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
@dataclass
class BlogPostInfo:
    """Information about a Confluence blog post."""
    id: str
    title: str
    type: str
    status: str
    space_key: str
    version: int
    created_by: Dict[str, Any]
    created_at: str
    updated_by: Dict[str, Any]
    updated_at: str
    body_html: str
    body_plain: str
    metadata: Dict[str, Any]
    
@dataclass
class CommentInfo:
    """Information about a Confluence comment."""
    id: str
    title: str
    type: str
    status: str
    container_id: str
    version: int
    created_by: Dict[str, Any]
    created_at: str
    updated_by: Dict[str, Any]
    updated_at: str
    body_html: str
    body_plain: str
    
@dataclass
class AttachmentInfo:
    """Information about a Confluence attachment."""
    id: str
    title: str
    file_name: str
    file_size: int
    media_type: str
    created_by: Dict[str, Any]
    created_at: str
    updated_by: Dict[str, Any]
    updated_at: str
    download_url: str
    metadata: Dict[str, Any]
    
@dataclass
class SearchResult:
    """Search result from Confluence."""
    id: str
    title: str
    type: str
    space_key: str
    excerpt: str
    url: str
    last_modified: str

class ConfluenceMCPServer(BaseMCPServer):
    """Confluence MCP Server for Atlassian Confluence operations."""
    
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        cloud: bool = True,
        timeout: int = 60,
        verify_ssl: bool = True,
        host: str = "127.0.0.1",
        port: int = 8006,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Confluence MCP Server.
        
        Args:
            url: Confluence instance URL
            username: Confluence username
            password: Confluence password or API token
            cloud: Use Confluence Cloud (True) or Server/Data Center (False)
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
            host: Host to run MCP server on
            port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        try:
            self.confluence_client = Confluence(
                url=url,
                username=username,
                password=password,
                cloud=cloud,
                timeout=timeout,
                verify_ssl=verify_ssl
            )
            
            # Test connection
            self.confluence_client.get_spaces(start=0, limit=1)
            self.connected = True
            self.is_cloud = cloud
            
        except Exception as e:
            self.connected = False
            self.confluence_client = None
            if debug:
                print(f"Confluence connection failed: {e}")
        
        # Initialize HTML to text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        
        # Initialize base class
        super().__init__(
            name="Confluence MCP Server",
            description="MCP server for Atlassian Confluence operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _check_connection(self) -> bool:
        """Check Confluence connection."""
        if not self.connected or not self.confluence_client:
            return False
        try:
            self.confluence_client.get_spaces(start=0, limit=1)
            return True
        except Exception:
            self.connected = False
            return False
    
    def _html_to_plain(self, html_content: str) -> str:
        """Convert HTML content to plain text."""
        if not html_content:
            return ""
        return self.html_converter.handle(html_content).strip()
    
    def _parse_space(self, space) -> SpaceInfo:
        """Parse Confluence space object."""
        return SpaceInfo(
            id=space.get('id', 0),
            key=space.get('key', ''),
            name=space.get('name', ''),
            type=space.get('type', 'global'),
            status=space.get('status', 'current'),
            description=space.get('description'),
            homepage_id=space.get('homepage', {}).get('id') if isinstance(space.get('homepage'), dict) else None,
            created_at=space.get('createdAt', ''),
            updated_at=space.get('updatedAt', ''),
            metadata={
                'description': space.get('description', {}),
                'icon': space.get('icon', {}),
                'homepage': space.get('homepage', {}),
                'settings': space.get('settings', {})
            }
        )
    
    def _parse_page(self, page, content: Optional[str] = None) -> PageInfo:
        """Parse Confluence page object."""
        # Get body content
        body_html = ""
        if content:
            body_html = content
        elif 'body' in page and 'storage' in page['body']:
            body_html = page['body']['storage']['value']
        
        # Get ancestors
        ancestors = []
        if 'ancestors' in page:
            for ancestor in page['ancestors']:
                ancestors.append({
                    'id': ancestor.get('id'),
                    'title': ancestor.get('title'),
                    'type': ancestor.get('type')
                })
        
        return PageInfo(
            id=page.get('id', ''),
            title=page.get('title', ''),
            type=page.get('type', 'page'),
            status=page.get('status', 'current'),
            space_key=page.get('space', {}).get('key', '') if isinstance(page.get('space'), dict) else page.get('spaceKey', ''),
            version=page.get('version', {}).get('number', 1) if isinstance(page.get('version'), dict) else 1,
            created_by=page.get('history', {}).get('createdBy', {}) if isinstance(page.get('history'), dict) else {},
            created_at=page.get('history', {}).get('createdDate', '') if isinstance(page.get('history'), dict) else '',
            updated_by=page.get('version', {}).get('by', {}) if isinstance(page.get('version'), dict) else {},
            updated_at=page.get('version', {}).get('when', '') if isinstance(page.get('version'), dict) else '',
            body_html=body_html,
            body_plain=self._html_to_plain(body_html),
            ancestors=ancestors,
            children=[],  # Will be populated separately if needed
            metadata={
                'labels': page.get('metadata', {}).get('labels', []),
                'properties': page.get('metadata', {}).get('properties', {})
            }
        )
    
    def _register_tools(self) -> None:
        """Register all Confluence-related tools."""
        self._register_space_tools()
        self._register_page_tools()
        self._register_blog_tools()
        self._register_comment_tools()
        self._register_attachment_tools()
        self._register_search_tools()
        self._register_content_tools()
    
    def _register_space_tools(self):
        """Register space management tools."""
        
        @self.mcp_server.tool()
        def list_spaces(
            space_type: str = "global",
            status: str = "current",
            limit: int = 50
        ) -> Dict[str, Any]:
            """List Confluence spaces.
            
            Args:
                space_type: Space type (global, personal)
                status: Space status (current, archived)
                limit: Maximum number of spaces to return
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                spaces = self.confluence_client.get_all_spaces(
                    space_type=space_type,
                    status=status,
                    limit=limit
                )
                
                space_list = []
                for space in spaces:
                    try:
                        space_info = self._parse_space(space)
                        space_list.append(asdict(space_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing space {space.get('key')}: {e}")
                        continue
                
                return {
                    "count": len(space_list),
                    "spaces": space_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_space(space_key: str) -> Dict[str, Any]:
            """Get detailed information about a space."""
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                space = self.confluence_client.get_space(
                    space_key,
                    expand='description,icon,homepage'
                )
                
                space_info = self._parse_space(space)
                
                return {
                    "space": asdict(space_info)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_space(
            space_key: str,
            name: str,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new Confluence space.
            
            Args:
                space_key: Space key (unique identifier)
                name: Space name
                description: Space description
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                space_data = {
                    'key': space_key,
                    'name': name
                }
                
                if description:
                    space_data['description'] = {'plain': {'value': description}}
                
                space = self.confluence_client.create_space(**space_data)
                space_info = self._parse_space(space)
                
                return {
                    "success": True,
                    "space": asdict(space_info),
                    "message": f"Space '{name}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_page_tools(self):
        """Register page management tools."""
        
        @self.mcp_server.tool()
        def list_pages(
            space_key: str,
            start: int = 0,
            limit: int = 50,
            status: str = "current"
        ) -> Dict[str, Any]:
            """List pages in a space.
            
            Args:
                space_key: Space key
                start: Start index for pagination
                limit: Maximum number of pages to return
                status: Page status (current, draft, archived)
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                pages = self.confluence_client.get_all_pages_from_space(
                    space=space_key,
                    start=start,
                    limit=limit,
                    status=status,
                    expand='version,history,space,ancestors,body.storage'
                )
                
                page_list = []
                for page in pages:
                    try:
                        page_info = self._parse_page(page)
                        page_list.append(asdict(page_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing page {page.get('id')}: {e}")
                        continue
                
                return {
                    "space": space_key,
                    "count": len(page_list),
                    "pages": page_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_page(
            page_id: str,
            include_content: bool = True
        ) -> Dict[str, Any]:
            """Get detailed information about a page.
            
            Args:
                page_id: Page ID
                include_content: Include page content in response
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                expand_fields = 'version,history,space,ancestors,body.storage'
                page = self.confluence_client.get_page_by_id(
                    page_id=page_id,
                    expand=expand_fields
                )
                
                # Get page content
                content = None
                if include_content:
                    try:
                        content = self.confluence_client.get_page_by_id(
                            page_id=page_id,
                            expand='body.storage'
                        ).get('body', {}).get('storage', {}).get('value', '')
                    except:
                        content = ""
                
                page_info = self._parse_page(page, content)
                
                return {
                    "page": asdict(page_info)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_page(
            space_key: str,
            title: str,
            body: str,
            parent_id: Optional[str] = None,
            editor: str = "storage"
        ) -> Dict[str, Any]:
            """Create a new page in Confluence.
            
            Args:
                space_key: Space key
                title: Page title
                body: Page content (HTML format)
                parent_id: Parent page ID (for nested pages)
                editor: Editor format (storage, editor2, view)
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                # Create page
                page = self.confluence_client.create_page(
                    space=space_key,
                    title=title,
                    body=body,
                    parent_id=parent_id,
                    type='page',
                    representation=editor
                )
                
                # Get created page with full details
                page_with_details = self.confluence_client.get_page_by_id(
                    page_id=page['id'],
                    expand='version,history,space,ancestors,body.storage'
                )
                
                page_info = self._parse_page(page_with_details, body)
                
                return {
                    "success": True,
                    "page": asdict(page_info),
                    "message": f"Page '{title}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def update_page(
            page_id: str,
            title: Optional[str] = None,
            body: Optional[str] = None,
            version: Optional[int] = None,
            editor: str = "storage"
        ) -> Dict[str, Any]:
            """Update an existing page.
            
            Args:
                page_id: Page ID
                title: New page title (optional)
                body: New page content (optional)
                version: Current page version (required for conflict resolution)
                editor: Editor format (storage, editor2, view)
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                # Get current page to retrieve version if not provided
                if version is None:
                    current_page = self.confluence_client.get_page_by_id(
                        page_id=page_id,
                        expand='version'
                    )
                    version = current_page.get('version', {}).get('number', 1)
                
                # Update page
                update_data = {}
                if title is not None:
                    update_data['title'] = title
                if body is not None:
                    update_data['body'] = body
                    update_data['representation'] = editor
                
                if not update_data:
                    return {"error": "No update data provided"}
                
                self.confluence_client.update_page(
                    page_id=page_id,
                    version=version + 1,
                    **update_data
                )
                
                # Get updated page
                updated_page = self.confluence_client.get_page_by_id(
                    page_id=page_id,
                    expand='version,history,space,ancestors,body.storage'
                )
                
                page_info = self._parse_page(updated_page, body)
                
                return {
                    "success": True,
                    "page": asdict(page_info),
                    "message": f"Page updated successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def delete_page(page_id: str) -> Dict[str, Any]:
            """Delete a page."""
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                # Get page info before deletion
                page = self.confluence_client.get_page_by_id(page_id)
                page_title = page.get('title', 'Unknown')
                
                # Delete page
                self.confluence_client.remove_page(page_id)
                
                return {
                    "success": True,
                    "page_id": page_id,
                    "page_title": page_title,
                    "message": f"Page '{page_title}' deleted successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_page_children(
            page_id: str,
            limit: int = 50
        ) -> Dict[str, Any]:
            """Get child pages of a page."""
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                children = self.confluence_client.get_page_child_by_type(
                    page_id=page_id,
                    type='page',
                    start=0,
                    limit=limit,
                    expand='version,history,body.storage'
                )
                
                child_list = []
                for child in children:
                    try:
                        page_info = self._parse_page(child)
                        child_list.append(asdict(page_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing child page {child.get('id')}: {e}")
                        continue
                
                return {
                    "parent_page_id": page_id,
                    "count": len(child_list),
                    "children": child_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_blog_tools(self):
        """Register blog post tools."""
        
        @self.mcp_server.tool()
        def list_blog_posts(
            space_key: str,
            start: int = 0,
            limit: int = 50,
            status: str = "current"
        ) -> Dict[str, Any]:
            """List blog posts in a space."""
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                blog_posts = self.confluence_client.get_all_pages_from_space(
                    space=space_key,
                    start=start,
                    limit=limit,
                    status=status,
                    content_type='blogpost',
                    expand='version,history,space,body.storage'
                )
                
                blog_list = []
                for post in blog_posts:
                    try:
                        blog_info = BlogPostInfo(
                            id=post.get('id', ''),
                            title=post.get('title', ''),
                            type=post.get('type', 'blogpost'),
                            status=post.get('status', 'current'),
                            space_key=post.get('space', {}).get('key', ''),
                            version=post.get('version', {}).get('number', 1),
                            created_by=post.get('history', {}).get('createdBy', {}),
                            created_at=post.get('history', {}).get('createdDate', ''),
                            updated_by=post.get('version', {}).get('by', {}),
                            updated_at=post.get('version', {}).get('when', ''),
                            body_html=post.get('body', {}).get('storage', {}).get('value', ''),
                            body_plain=self._html_to_plain(
                                post.get('body', {}).get('storage', {}).get('value', '')
                            ),
                            metadata={
                                'labels': post.get('metadata', {}).get('labels', []),
                                'properties': post.get('metadata', {}).get('properties', {})
                            }
                        )
                        blog_list.append(asdict(blog_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing blog post {post.get('id')}: {e}")
                        continue
                
                return {
                    "space": space_key,
                    "count": len(blog_list),
                    "blog_posts": blog_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_blog_post(
            space_key: str,
            title: str,
            body: str,
            editor: str = "storage"
        ) -> Dict[str, Any]:
            """Create a new blog post."""
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                blog_post = self.confluence_client.create_page(
                    space=space_key,
                    title=title,
                    body=body,
                    type='blogpost',
                    representation=editor
                )
                
                return {
                    "success": True,
                    "blog_post_id": blog_post['id'],
                    "title": title,
                    "message": f"Blog post '{title}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_comment_tools(self):
        """Register comment tools."""
        
        @self.mcp_server.tool()
        def list_comments(
            content_id: str,
            depth: str = "all",
            limit: int = 100
        ) -> Dict[str, Any]:
            """List comments on a page or blog post.
            
            Args:
                content_id: Page or blog post ID
                depth: Comment depth (all, root, nested)
                limit: Maximum number of comments to return
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                comments = self.confluence_client.get_page_comments(
                    page_id=content_id,
                    depth=depth,
                    start=0,
                    limit=limit,
                    expand='version,history,body.storage'
                )
                
                comment_list = []
                for comment in comments:
                    try:
                        comment_info = CommentInfo(
                            id=comment.get('id', ''),
                            title=comment.get('title', ''),
                            type=comment.get('type', 'comment'),
                            status=comment.get('status', 'current'),
                            container_id=comment.get('container', {}).get('id', ''),
                            version=comment.get('version', {}).get('number', 1),
                            created_by=comment.get('history', {}).get('createdBy', {}),
                            created_at=comment.get('history', {}).get('createdDate', ''),
                            updated_by=comment.get('version', {}).get('by', {}),
                            updated_at=comment.get('version', {}).get('when', ''),
                            body_html=comment.get('body', {}).get('storage', {}).get('value', ''),
                            body_plain=self._html_to_plain(
                                comment.get('body', {}).get('storage', {}).get('value', '')
                            )
                        )
                        comment_list.append(asdict(comment_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing comment {comment.get('id')}: {e}")
                        continue
                
                return {
                    "content_id": content_id,
                    "count": len(comment_list),
                    "comments": comment_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def add_comment(
            content_id: str,
            body: str,
            parent_comment_id: Optional[str] = None,
            editor: str = "storage"
        ) -> Dict[str, Any]:
            """Add a comment to a page or blog post."""
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                comment = self.confluence_client.add_comment(
                    page_id=content_id,
                    text=body,
                    parent_id=parent_comment_id,
                    representation=editor
                )
                
                return {
                    "success": True,
                    "comment_id": comment['id'],
                    "message": "Comment added successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_attachment_tools(self):
        """Register attachment tools."""
        
        @self.mcp_server.tool()
        def list_attachments(
            content_id: str,
            limit: int = 50
        ) -> Dict[str, Any]:
            """List attachments on a page or blog post."""
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                attachments = self.confluence_client.get_attachments_from_content(
                    content_id,
                    start=0,
                    limit=limit,
                    expand='version,history'
                )
                
                attachment_list = []
                for attachment in attachments:
                    try:
                        attachment_info = AttachmentInfo(
                            id=attachment.get('id', ''),
                            title=attachment.get('title', ''),
                            file_name=attachment.get('_links', {}).get('download', ''),
                            file_size=attachment.get('extensions', {}).get('fileSize', 0),
                            media_type=attachment.get('metadata', {}).get('mediaType', ''),
                            created_by=attachment.get('version', {}).get('by', {}),
                            created_at=attachment.get('version', {}).get('when', ''),
                            updated_by=attachment.get('version', {}).get('by', {}),
                            updated_at=attachment.get('version', {}).get('when', ''),
                            download_url=attachment.get('_links', {}).get('download', ''),
                            metadata=attachment.get('metadata', {})
                        )
                        attachment_list.append(asdict(attachment_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing attachment {attachment.get('id')}: {e}")
                        continue
                
                return {
                    "content_id": content_id,
                    "count": len(attachment_list),
                    "attachments": attachment_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_search_tools(self):
        """Register search tools."""
        
        @self.mcp_server.tool()
        def search_content(
            query: str,
            space_key: Optional[str] = None,
            content_type: Optional[str] = None,
            limit: int = 50
        ) -> Dict[str, Any]:
            """Search for content in Confluence.
            
            Args:
                query: Search query
                space_key: Limit search to specific space
                content_type: Limit search to specific content type (page, blogpost)
                limit: Maximum number of results
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                # Build CQL (Confluence Query Language) query
                cql_parts = [f'title ~ "{query}" OR text ~ "{query}"']
                
                if space_key:
                    cql_parts.append(f'space = "{space_key}"')
                
                if content_type:
                    cql_parts.append(f'type = "{content_type}"')
                
                cql = ' AND '.join(cql_parts)
                
                results = self.confluence_client.cql(
                    cql=cql,
                    start=0,
                    limit=limit,
                    expand='content.version,content.space'
                )
                
                result_list = []
                for result in results.get('results', []):
                    try:
                        content = result.get('content', {})
                        search_result = SearchResult(
                            id=content.get('id', ''),
                            title=content.get('title', ''),
                            type=content.get('type', ''),
                            space_key=content.get('space', {}).get('key', ''),
                            excerpt=result.get('excerpt', ''),
                            url=content.get('_links', {}).get('webui', ''),
                            last_modified=content.get('version', {}).get('when', '')
                        )
                        result_list.append(asdict(search_result))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing search result: {e}")
                        continue
                
                return {
                    "query": query,
                    "cql": cql,
                    "total_size": results.get('totalSize', 0),
                    "count": len(result_list),
                    "results": result_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_content_tools(self):
        """Register content export/import tools."""
        
        @self.mcp_server.tool()
        def export_page(
            page_id: str,
            export_format: str = "pdf"
        ) -> Dict[str, Any]:
            """Export a page in specified format.
            
            Args:
                page_id: Page ID to export
                export_format: Export format (pdf, word, html)
            """
            if not self._check_connection():
                return {"error": "Confluence connection not available"}
            
            try:
                # Note: This is a simplified example
                # Actual export requires different API calls based on Confluence version
                
                page = self.confluence_client.get_page_by_id(
                    page_id=page_id,
                    expand='body.storage'
                )
                
                content = page.get('body', {}).get('storage', {}).get('value', '')
                
                if export_format == "html":
                    # Return HTML content
                    return {
                        "success": True,
                        "page_id": page_id,
                        "title": page.get('title', ''),
                        "format": "html",
                        "content": content,
                        "message": "Page exported as HTML"
                    }
                elif export_format == "plain":
                    # Return plain text
                    plain_text = self._html_to_plain(content)
                    return {
                        "success": True,
                        "page_id": page_id,
                        "title": page.get('title', ''),
                        "format": "plain",
                        "content": plain_text,
                        "message": "Page exported as plain text"
                    }
                else:
                    return {
                        "error": f"Export format '{export_format}' not supported in this implementation"
                    }
            except Exception as e:
                return {"error": str(e)}


# CLI interface
if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Confluence MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="MCP server host")
    parser.add_argument("--port", type=int, default=8006, help="MCP server port")
    parser.add_argument("--url", required=True, help="Confluence instance URL")
    parser.add_argument("--username", help="Confluence username")
    parser.add_argument("--password", help="Confluence password or API token")
    parser.add_argument("--server", action="store_true", 
                       help="Use Confluence Server (default: Cloud)")
    parser.add_argument("--transport", default="stdio", 
                       choices=['stdio', 'sse', 'streamable-http'],
                       help="Transport type")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Get credentials from environment if not provided
    username = args.username or os.environ.get('CONFLUENCE_USERNAME')
    password = args.password or os.environ.get('CONFLUENCE_PASSWORD')
    
    server = ConfluenceMCPServer(
        url=args.url,
        username=username,
        password=password,
        cloud=not args.server,
        host=args.host,
        port=args.port,
        transport=args.transport,
        debug=args.debug
    )
    
    print(f"Starting Confluence MCP Server on {args.host}:{args.port}")
    print(f"Confluence URL: {args.url}")
    print(f"Mode: {'Server' if args.server else 'Cloud'}")
    print(f"Transport: {args.transport}")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down Confluence MCP Server...")
    except Exception as e:
        print(f"Error: {e}")