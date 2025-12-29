from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import httpx
import json
import yaml
from urllib.parse import urlparse, urljoin
from mcp_arena.mcp.server import BaseMCPServer


@dataclass
class APIResponse:
    """Standard API response structure"""
    status_code: int
    headers: Dict[str, str]
    data: Any
    url: str
    method: str
    timestamp: datetime = field(default_factory=datetime.now)
    elapsed_ms: Optional[float] = None


@dataclass
class APIConfig:
    """API configuration for reusable endpoints"""
    name: str
    base_url: str
    default_headers: Dict[str, str] = field(default_factory=dict)
    default_auth: Optional[Dict[str, Any]] = field(default=None)
    endpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SavedRequest:
    """Saved API request template"""
    name: str
    url: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Optional[Any] = field(default=None)
    json_data: Optional[Any] = field(default=None)
    auth: Optional[Dict[str, Any]] = field(default=None)
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class HTTPMethod(str, Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(str, Enum):
    """Authentication types"""
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    NONE = "none"


class GenericAPIMCPServer(BaseMCPServer):
    """Generic API MCP Server for making any API call with any structure."""
    
    def __init__(
        self,
        default_timeout: int = 30,
        default_verify_ssl: bool = True,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Generic API MCP Server.
        
        Args:
            default_timeout: Default timeout for API requests in seconds
            default_verify_ssl: Default SSL verification setting
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.default_timeout = default_timeout
        self.default_verify_ssl = default_verify_ssl
        self.api_configs: Dict[str, APIConfig] = {}
        self.saved_requests: Dict[str, SavedRequest] = {}
        
        # Initialize base class
        super().__init__(
            name="Generic API MCP Server",
            description="MCP server for making any API call with any structure",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all API-related tools."""
        self._register_basic_api_tools()
        self._register_config_tools()
        self._register_saved_request_tools()
    
    def _register_basic_api_tools(self):
        """Register basic API calling tools."""
        
        @self.mcp_server.tool()
        def make_api_request(
            url: str,
            method: HTTPMethod = HTTPMethod.GET,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            data: Optional[Any] = None,
            json_data: Optional[Any] = None,
            timeout: Optional[int] = None,
            auth: Optional[Dict[str, Any]] = None,
            verify_ssl: Optional[bool] = None
        ) -> Dict[str, Any]:
            """
            Make an API call to any endpoint.
            
            Args:
                url: The full URL to call
                method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
                headers: HTTP headers as key-value pairs
                params: Query parameters as key-value pairs
                data: Request body data (for form data, text, etc.)
                json_data: JSON data for request body
                timeout: Request timeout in seconds (default: 30)
                auth: Authentication configuration
                verify_ssl: Verify SSL certificates (default: True)
                
            Returns:
                API response with status, headers, and data
            """
            return self._make_api_request_impl(
                url=url,
                method=method,
                headers=headers,
                params=params,
                data=data,
                json_data=json_data,
                timeout=timeout,
                auth=auth,
                verify_ssl=verify_ssl
            )
        
        @self.mcp_server.tool()
        def test_endpoint(
            url: str,
            expected_status: Optional[int] = None,
            method: HTTPMethod = HTTPMethod.GET,
            timeout: int = 10
        ) -> Dict[str, Any]:
            """
            Test if an API endpoint is reachable and responding.
            
            Args:
                url: The URL to test
                expected_status: Expected HTTP status code (e.g., 200 for OK)
                method: HTTP method to use for testing
                timeout: Request timeout in seconds
                
            Returns:
                Test results including reachability and response time
            """
            return self._test_endpoint_impl(
                url=url,
                expected_status=expected_status,
                method=method,
                timeout=timeout
            )
    
    def _register_config_tools(self):
        """Register API configuration tools."""
        
        @self.mcp_server.tool()
        def register_api(
            name: str,
            base_url: str,
            default_headers: Optional[Dict[str, str]] = None,
            default_auth: Optional[Dict[str, Any]] = None,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Register an API configuration for reusable API patterns.
            
            Args:
                name: Unique name for the API configuration
                base_url: Base URL for all endpoints (e.g., https://api.example.com/v1)
                default_headers: Default headers for all requests to this API
                default_auth: Default authentication configuration
                description: Description of the API
                
            Returns:
                Registration status and configuration details
            """
            try:
                config = APIConfig(
                    name=name,
                    base_url=base_url.rstrip("/"),
                    default_headers=default_headers or {},
                    default_auth=default_auth,
                    description=description
                )
                
                self.api_configs[name] = config
                
                return {
                    "status": "success",
                    "message": f"API '{name}' registered successfully",
                    "config": asdict(config)
                }
                
            except Exception as e:
                return {"error": f"Failed to register API: {str(e)}"}
        
        @self.mcp_server.tool()
        def call_registered_api(
            api_name: str,
            endpoint: str,
            method: HTTPMethod = HTTPMethod.GET,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            data: Optional[Any] = None,
            json_data: Optional[Any] = None,
            timeout: Optional[int] = None,
            auth_override: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Make an API call using a registered API configuration.
            
            Args:
                api_name: Name of the registered API
                endpoint: API endpoint path (e.g., "/users" or "users")
                method: HTTP method
                headers: Additional headers to merge with defaults
                params: Query parameters
                data: Request body data
                json_data: JSON data for request body
                timeout: Request timeout override
                auth_override: Authentication override
                
            Returns:
                API response
            """
            try:
                if api_name not in self.api_configs:
                    return {"error": f"API '{api_name}' not found. Register it first using register_api."}
                
                config = self.api_configs[api_name]
                
                # Build full URL
                endpoint = endpoint.lstrip("/")
                full_url = f"{config.base_url}/{endpoint}"
                
                # Merge headers
                merged_headers = config.default_headers.copy()
                if headers:
                    merged_headers.update(headers)
                
                # Use config auth or override
                auth = auth_override if auth_override else config.default_auth
                
                # Make the request
                return self._make_api_request_impl(
                    url=full_url,
                    method=method,
                    headers=merged_headers,
                    params=params,
                    data=data,
                    json_data=json_data,
                    timeout=timeout,
                    auth=auth
                )
                
            except Exception as e:
                return {"error": f"Failed to call API: {str(e)}"}
        
        @self.mcp_server.tool()
        def list_registered_apis() -> Dict[str, Any]:
            """List all registered API configurations."""
            apis = {}
            for name, config in self.api_configs.items():
                apis[name] = {
                    "base_url": config.base_url,
                    "description": config.description,
                    "default_headers_count": len(config.default_headers),
                    "has_auth": config.default_auth is not None,
                    "created_at": config.created_at.isoformat()
                }
            
            return {"apis": apis}
        
        @self.mcp_server.tool()
        def delete_api_config(api_name: str) -> Dict[str, Any]:
            """
            Delete a registered API configuration.
            
            Args:
                api_name: Name of the API configuration to delete
                
            Returns:
                Deletion status
            """
            if api_name not in self.api_configs:
                return {"error": f"API '{api_name}' not found"}
            
            del self.api_configs[api_name]
            return {"status": "success", "message": f"API '{api_name}' deleted successfully"}
    
    def _register_saved_request_tools(self):
        """Register saved request template tools."""
        
        @self.mcp_server.tool()
        def save_request(
            name: str,
            url: str,
            method: HTTPMethod = HTTPMethod.GET,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            data: Optional[Any] = None,
            json_data: Optional[Any] = None,
            auth: Optional[Dict[str, Any]] = None,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Save an API request as a template for reuse.
            
            Args:
                name: Unique name for the saved request
                url: The URL (can include {variables} for templating)
                method: HTTP method
                headers: Default headers
                params: Default query parameters
                data: Default form/data
                json_data: Default JSON data (can include {variables})
                auth: Authentication configuration
                description: Description of the request
                
            Returns:
                Saved request information
            """
            try:
                saved_request = SavedRequest(
                    name=name,
                    url=url,
                    method=method,
                    headers=headers or {},
                    params=params or {},
                    data=data,
                    json_data=json_data,
                    auth=auth,
                    description=description
                )
                
                self.saved_requests[name] = saved_request
                
                return {
                    "status": "success",
                    "message": f"Request '{name}' saved successfully",
                    "request": asdict(saved_request)
                }
                
            except Exception as e:
                return {"error": f"Failed to save request: {str(e)}"}
        
        @self.mcp_server.tool()
        def execute_saved_request(
            name: str,
            variables: Optional[Dict[str, Any]] = None,
            override_headers: Optional[Dict[str, str]] = None,
            override_params: Optional[Dict[str, Any]] = None,
            override_data: Optional[Any] = None,
            override_json: Optional[Any] = None
        ) -> Dict[str, Any]:
            """
            Execute a saved API request template with variable substitution.
            
            Args:
                name: Name of the saved request
                variables: Variables to substitute in URL, params, and JSON
                override_headers: Headers to override/merge with saved headers
                override_params: Parameters to override/merge with saved params
                override_data: Data to override saved data
                override_json: JSON data to override saved json_data
                
            Returns:
                API response
            """
            try:
                if name not in self.saved_requests:
                    return {"error": f"Saved request '{name}' not found"}
                
                template = self.saved_requests[name]
                variables = variables or {}
                
                # Substitute variables in URL
                url = template.url
                for key, value in variables.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in url:
                        url = url.replace(placeholder, str(value))
                
                # Prepare headers
                headers = template.headers.copy()
                if override_headers:
                    headers.update(override_headers)
                
                # Prepare params
                params = template.params.copy()
                if override_params:
                    params.update(override_params)
                
                # Substitute variables in params
                for key, value in params.items():
                    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                        var_name = value[1:-1]
                        if var_name in variables:
                            params[key] = variables[var_name]
                
                # Prepare JSON data with variable substitution
                json_data = template.json_data
                if json_data is not None:
                    json_data = self._substitute_variables(json_data, variables)
                    if override_json is not None:
                        # Deep merge override JSON
                        if isinstance(json_data, dict) and isinstance(override_json, dict):
                            json_data = {**json_data, **override_json}
                        else:
                            json_data = override_json
                
                # Prepare form/data
                data = override_data if override_data is not None else template.data
                
                # Make the request
                return self._make_api_request_impl(
                    url=url,
                    method=template.method,
                    headers=headers,
                    params=params,
                    data=data,
                    json_data=json_data,
                    auth=template.auth
                )
                
            except Exception as e:
                return {"error": f"Failed to execute saved request: {str(e)}"}
        
        @self.mcp_server.tool()
        def list_saved_requests() -> Dict[str, Any]:
            """List all saved API request templates."""
            requests = {}
            for name, req in self.saved_requests.items():
                requests[name] = {
                    "url": req.url,
                    "method": req.method,
                    "description": req.description,
                    "has_auth": req.auth is not None,
                    "created_at": req.created_at.isoformat()
                }
            
            return {"saved_requests": requests}
    
    def _make_api_request_impl(
        self,
        url: str,
        method: HTTPMethod = HTTPMethod.GET,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        timeout: Optional[int] = None,
        auth: Optional[Dict[str, Any]] = None,
        verify_ssl: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Implementation of make_api_request."""
        try:
            # Prepare request parameters
            request_timeout = timeout or self.default_timeout
            request_verify_ssl = verify_ssl if verify_ssl is not None else self.default_verify_ssl
            
            # Prepare headers
            request_headers = headers or {}
            
            # Prepare authentication
            auth_obj = self._prepare_auth(auth) if auth else None
            
            # Handle API key auth in headers
            if auth and auth.get("type") == AuthType.API_KEY:
                api_key_name = auth.get("name", "X-API-Key")
                api_key_value = auth.get("key", "")
                api_key_location = auth.get("location", "header")
                
                if api_key_location == "header":
                    request_headers[api_key_name] = api_key_value
                elif api_key_location == "query":
                    params = params or {}
                    params[api_key_name] = api_key_value
            
            # Prepare request kwargs
            request_kwargs = {
                "headers": request_headers,
                "params": params,
                "timeout": request_timeout,
                "verify": request_verify_ssl
            }
            
            if auth_obj:
                request_kwargs["auth"] = auth_obj
            
            # Make request
            start_time = datetime.now()
            with httpx.Client() as client:
                if method == HTTPMethod.GET:
                    response = client.get(url, **request_kwargs)
                elif method == HTTPMethod.POST:
                    if json_data is not None:
                        request_kwargs["json"] = json_data
                    elif data is not None:
                        request_kwargs["data"] = self._serialize_data(data)
                    response = client.post(url, **request_kwargs)
                elif method == HTTPMethod.PUT:
                    if json_data is not None:
                        request_kwargs["json"] = json_data
                    elif data is not None:
                        request_kwargs["data"] = self._serialize_data(data)
                    response = client.put(url, **request_kwargs)
                elif method == HTTPMethod.DELETE:
                    response = client.delete(url, **request_kwargs)
                elif method == HTTPMethod.PATCH:
                    if json_data is not None:
                        request_kwargs["json"] = json_data
                    elif data is not None:
                        request_kwargs["data"] = self._serialize_data(data)
                    response = client.patch(url, **request_kwargs)
                elif method == HTTPMethod.HEAD:
                    response = client.head(url, **request_kwargs)
                elif method == HTTPMethod.OPTIONS:
                    response = client.options(url, **request_kwargs)
                else:
                    return {"error": f"Unsupported HTTP method: {method}"}
            
            # Calculate elapsed time
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            # Create response object
            api_response = APIResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                data=response_data,
                url=str(response.url),
                method=method,
                elapsed_ms=elapsed_ms
            )
            
            return asdict(api_response)
            
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def _test_endpoint_impl(
        self,
        url: str,
        expected_status: Optional[int] = None,
        method: HTTPMethod = HTTPMethod.GET,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Implementation of test_endpoint."""
        try:
            start_time = datetime.now()
            with httpx.Client() as client:
                response = client.request(
                    method=method,
                    url=url,
                    timeout=timeout
                )
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "reachable": True,
                "status_code": response.status_code,
                "response_time_ms": round(elapsed_ms, 2),
                "url": str(response.url)
            }
            
            if expected_status is not None:
                result["status_match"] = response.status_code == expected_status
                result["expected_status"] = expected_status
            
            return result
            
        except httpx.RequestError as e:
            return {
                "reachable": False,
                "error": str(e),
                "url": url
            }
        except Exception as e:
            return {
                "reachable": False,
                "error": f"Unexpected error: {str(e)}",
                "url": url
            }
    
    def _prepare_auth(self, auth_config: Dict[str, Any]) -> Optional[httpx.Auth]:
        """Prepare authentication object from configuration."""
        if not auth_config:
            return None
        
        auth_type = auth_config.get("type", "none")
        
        if auth_type == AuthType.BASIC:
            return httpx.BasicAuth(
                username=auth_config.get("username", ""),
                password=auth_config.get("password", "")
            )
        elif auth_type == AuthType.BEARER:
            token = auth_config.get("token", "")
            if token.startswith("Bearer "):
                token = token[7:]
            return httpx.BearerToken(token=token)
        elif auth_type == AuthType.API_KEY:
            # API key auth is handled in _make_api_request_impl
            return None
        elif auth_type == AuthType.OAUTH2:
            # For OAuth2, we expect a bearer token
            token = auth_config.get("access_token", "")
            return httpx.BearerToken(token=token)
        else:
            return None
    
    def _serialize_data(self, data: Any) -> Any:
        """Serialize data for requests."""
        if isinstance(data, (dict, list)):
            return json.dumps(data) if not isinstance(data, str) else data
        return data
    
    def _substitute_variables(self, template: Any, variables: Dict[str, Any]) -> Any:
        """Recursively substitute variables in template."""
        if isinstance(template, dict):
            result = {}
            for key, value in template.items():
                result[key] = self._substitute_variables(value, variables)
            return result
        elif isinstance(template, list):
            return [self._substitute_variables(item, variables) for item in template]
        elif isinstance(template, str) and template.startswith("{") and template.endswith("}"):
            var_name = template[1:-1]
            return variables.get(var_name, template)
        else:
            return template