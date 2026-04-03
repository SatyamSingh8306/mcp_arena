"""
Browser Automation MCP Server
A comprehensive browser automation server using Playwright for web automation,
scraping, testing, and more.
"""
from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import os
import json
import base64
from pathlib import Path
from mcp_arena.mcp.server import BaseMCPServer

# Lazy imports for playwright
_playwright = None
_async_api = None
_sync_api = None

def _import_playwright():
    """Lazily import playwright modules."""
    global _playwright, _sync_api
    if _playwright is None:
        try:
            from playwright.sync_api import sync_playwright
            _sync_api = sync_playwright
            _playwright = True
        except ImportError:
            raise ImportError(
                "playwright is required for BrowserMCPServer. "
                "Install it with: pip install playwright && playwright install"
            )
    return _sync_api


class BrowserType(str, Enum):
    """Browser type enumeration."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ViewportPreset(str, Enum):
    """Viewport preset sizes."""
    MOBILE = "mobile"  # 375x667
    TABLET = "tablet"  # 768x1024
    DESKTOP = "desktop"  # 1920x1080
    FULL_HD = "full_hd"  # 1920x1080
    LAPTOP = "laptop"  # 1366x768


@dataclass
class BrowserSession:
    """Browser session information."""
    session_id: str
    browser_type: str
    headless: bool
    viewport_width: int
    viewport_height: int
    user_agent: Optional[str]
    created_at: str
    current_url: Optional[str] = None
    current_title: Optional[str] = None
    pages_count: int = 1
    is_active: bool = True


@dataclass
class PageElement:
    """Page element information."""
    tag_name: str
    text: Optional[str]
    attributes: Dict[str, str]
    is_visible: bool
    is_enabled: bool
    bounding_box: Optional[Dict[str, float]]
    selector: str


@dataclass
class FormField:
    """Form field information."""
    name: Optional[str]
    type: str
    value: Optional[str]
    is_required: bool
    is_readonly: bool
    placeholder: Optional[str]
    selector: str


@dataclass
class Cookie:
    """Cookie information."""
    name: str
    value: str
    domain: str
    path: str
    expires: Optional[float]
    http_only: bool
    secure: bool
    same_site: Optional[str]


@dataclass
class NetworkRequest:
    """Network request information."""
    url: str
    method: str
    headers: Dict[str, str]
    post_data: Optional[str]
    resource_type: str
    status: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    timing: Optional[Dict[str, float]] = None


class BrowserMCPServer(BaseMCPServer):
    """Browser Automation MCP Server for web automation, scraping, and testing."""

    # Class-level storage for browser instances
    _instances: Dict[str, Any] = {}
    _playwright_context = None
    _active_session: Optional[str] = None

    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        user_agent: Optional[str] = None,
        downloads_path: Optional[str] = None,
        timeout: int = 30000,
        slow_mo: int = 0,
        proxy: Optional[Dict[str, str]] = None,
        ignore_https_errors: bool = False,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Browser Automation MCP Server.

        Args:
            browser_type: Browser to use (chromium, firefox, webkit)
            headless: Run browser in headless mode
            viewport_width: Viewport width in pixels
            viewport_height: Viewport height in pixels
            user_agent: Custom user agent string
            downloads_path: Path for downloads
            timeout: Default timeout in milliseconds
            slow_mo: Slow down operations by specified milliseconds
            proxy: Proxy configuration
            ignore_https_errors: Ignore HTTPS certificate errors
            host: Host to run MCP server on
            port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.browser_type = browser_type
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.user_agent = user_agent
        self.downloads_path = downloads_path or os.path.join(os.getcwd(), "downloads")
        self.timeout = timeout
        self.slow_mo = slow_mo
        self.proxy = proxy
        self.ignore_https_errors = ignore_https_errors

        # Ensure downloads directory exists
        Path(self.downloads_path).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="Browser Automation MCP Server",
            description="MCP server for browser automation, web scraping, form filling, screenshots, and more using Playwright",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )

    def _get_browser(self, session_id: Optional[str] = None):
        """Get or create browser instance."""
        if session_id and session_id in self._instances:
            return self._instances[session_id]

        # Initialize playwright if needed
        sync_playwright = _import_playwright()

        if self._playwright_context is None:
            self._playwright_context = sync_playwright().start()

        # Create new browser
        playwright = self._playwright_context
        browser_launcher = getattr(playwright, self.browser_type.value)

        launch_options = {
            "headless": self.headless,
            "slow_mo": self.slow_mo,
            "downloads_path": self.downloads_path,
        }

        if self.proxy:
            launch_options["proxy"] = self.proxy

        browser = browser_launcher.launch(**launch_options)

        # Create context
        context_options = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "ignore_https_errors": self.ignore_https_errors,
        }

        if self.user_agent:
            context_options["user_agent"] = self.user_agent

        context = browser.new_context(**context_options)

        # Set default timeout
        context.set_default_timeout(self.timeout)

        # Create page
        page = context.new_page()

        # Store instance
        import uuid
        new_session_id = session_id or str(uuid.uuid4())[:8]
        self._instances[new_session_id] = {
            "browser": browser,
            "context": context,
            "page": page,
            "info": BrowserSession(
                session_id=new_session_id,
                browser_type=self.browser_type.value,
                headless=self.headless,
                viewport_width=self.viewport_width,
                viewport_height=self.viewport_height,
                user_agent=self.user_agent,
                created_at=datetime.now().isoformat()
            )
        }

        if self._active_session is None:
            self._active_session = new_session_id

        return self._instances[new_session_id]

    def _get_active_page(self):
        """Get the active page."""
        if self._active_session is None:
            self._get_browser()
        instance = self._instances.get(self._active_session)
        if instance:
            return instance["page"]
        return None

    def _register_tools(self) -> None:
        """Register all browser automation tools."""
        self._register_session_tools()
        self._register_navigation_tools()
        self._register_interaction_tools()
        self._register_form_tools()
        self._register_extraction_tools()
        self._register_screenshot_tools()
        self._register_network_tools()
        self._register_advanced_tools()

    def _register_session_tools(self):
        """Register browser session management tools."""

        @self.mcp_server.tool()
        def create_browser_session(
            browser_type: str = "chromium",
            headless: bool = True,
            viewport_width: int = 1920,
            viewport_height: int = 1080,
            user_agent: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new browser session.

            Args:
                browser_type: Browser to use (chromium, firefox, webkit)
                headless: Run in headless mode
                viewport_width: Viewport width
                viewport_height: Viewport height
                user_agent: Custom user agent
            """
            try:
                # Temporarily update settings
                original = {
                    "browser_type": self.browser_type,
                    "headless": self.headless,
                    "viewport_width": self.viewport_width,
                    "viewport_height": self.viewport_height,
                    "user_agent": self.user_agent
                }

                self.browser_type = BrowserType(browser_type)
                self.headless = headless
                self.viewport_width = viewport_width
                self.viewport_height = viewport_height
                self.user_agent = user_agent

                instance = self._get_browser()

                # Restore original settings
                self.browser_type = original["browser_type"]
                self.headless = original["headless"]
                self.viewport_width = original["viewport_width"]
                self.viewport_height = original["viewport_height"]
                self.user_agent = original["user_agent"]

                return {
                    "success": True,
                    "session": asdict(instance["info"])
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def list_browser_sessions() -> Dict[str, Any]:
            """List all active browser sessions."""
            try:
                sessions = []
                for session_id, instance in self._instances.items():
                    info = instance["info"]
                    info.current_url = instance["page"].url
                    info.current_title = instance["page"].title()
                    info.pages_count = len(instance["context"].pages)
                    sessions.append(asdict(info))

                return {
                    "count": len(sessions),
                    "active_session": self._active_session,
                    "sessions": sessions
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def switch_session(session_id: str) -> Dict[str, Any]:
            """Switch to a different browser session."""
            try:
                if session_id not in self._instances:
                    return {"error": f"Session {session_id} not found"}

                self._active_session = session_id
                instance = self._instances[session_id]
                info = instance["info"]
                info.current_url = instance["page"].url

                return {
                    "success": True,
                    "active_session": session_id,
                    "current_url": instance["page"].url
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def close_browser_session(session_id: Optional[str] = None) -> Dict[str, Any]:
            """Close a browser session."""
            try:
                target_id = session_id or self._active_session
                if target_id is None:
                    return {"error": "No active session to close"}

                if target_id not in self._instances:
                    return {"error": f"Session {target_id} not found"}

                instance = self._instances[target_id]
                instance["context"].close()
                instance["browser"].close()

                del self._instances[target_id]

                if self._active_session == target_id:
                    self._active_session = next(iter(self._instances.keys()), None)

                return {
                    "success": True,
                    "message": f"Session {target_id} closed",
                    "remaining_sessions": list(self._instances.keys())
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def close_all_sessions() -> Dict[str, Any]:
            """Close all browser sessions."""
            try:
                closed = []
                for session_id in list(self._instances.keys()):
                    instance = self._instances[session_id]
                    try:
                        instance["context"].close()
                        instance["browser"].close()
                        closed.append(session_id)
                    except:
                        pass

                self._instances.clear()
                self._active_session = None

                if self._playwright_context:
                    self._playwright_context.stop()
                    self._playwright_context = None

                return {
                    "success": True,
                    "closed_sessions": closed,
                    "message": f"Closed {len(closed)} sessions"
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_navigation_tools(self):
        """Register navigation tools."""

        @self.mcp_server.tool()
        def navigate(
            url: str,
            wait_until: str = "load",
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Navigate to a URL.

            Args:
                url: URL to navigate to
                wait_until: When to consider navigation done (load, domcontentloaded, networkidle)
                timeout: Navigation timeout in milliseconds
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session. Create a session first."}

                response = page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=timeout or self.timeout
                )

                return {
                    "success": True,
                    "url": page.url,
                    "title": page.title(),
                    "status": response.status if response else None,
                    "redirected": response.url != url if response else False
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def go_back(timeout: Optional[int] = None) -> Dict[str, Any]:
            """Navigate back in browser history."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                response = page.go_back(timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "url": page.url,
                    "title": page.title()
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def go_forward(timeout: Optional[int] = None) -> Dict[str, Any]:
            """Navigate forward in browser history."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                response = page.go_forward(timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "url": page.url,
                    "title": page.title()
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def refresh(timeout: Optional[int] = None) -> Dict[str, Any]:
            """Refresh the current page."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                response = page.reload(timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "url": page.url,
                    "title": page.title()
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_current_url() -> Dict[str, Any]:
            """Get the current page URL."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                return {
                    "url": page.url,
                    "title": page.title()
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_interaction_tools(self):
        """Register page interaction tools."""

        @self.mcp_server.tool()
        def click(
            selector: str,
            button: str = "left",
            click_count: int = 1,
            delay: int = 0,
            force: bool = False,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Click an element on the page.

            Args:
                selector: CSS selector or XPath
                button: Mouse button (left, right, middle)
                click_count: Number of clicks (1 for single, 2 for double)
                delay: Delay between mousedown and mouseup in ms
                force: Skip actionability checks
                timeout: Timeout in milliseconds
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.click(
                    selector,
                    button=button,
                    click_count=click_count,
                    delay=delay,
                    force=force,
                    timeout=timeout or self.timeout
                )

                return {
                    "success": True,
                    "selector": selector,
                    "message": f"Clicked element: {selector}"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def double_click(selector: str, timeout: Optional[int] = None) -> Dict[str, Any]:
            """Double click an element."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.dblclick(selector, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def hover(selector: str, timeout: Optional[int] = None) -> Dict[str, Any]:
            """Hover over an element."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.hover(selector, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def type_text(
            selector: str,
            text: str,
            delay: int = 0,
            clear: bool = True,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Type text into an input field.

            Args:
                selector: CSS selector for the input element
                text: Text to type
                delay: Delay between keystrokes in ms
                clear: Clear field before typing
                timeout: Timeout in milliseconds
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                if clear:
                    page.fill(selector, "", timeout=timeout or self.timeout)

                page.type(selector, text, delay=delay, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector,
                    "text_length": len(text)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def fill_input(
            selector: str,
            value: str,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Fill an input field with a value (faster than type)."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.fill(selector, value, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector,
                    "value_length": len(value)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def press_key(
            selector: Optional[str],
            key: str,
            delay: int = 0
        ) -> Dict[str, Any]:
            """Press a key or key combination.

            Args:
                selector: CSS selector for element (or None for page-level)
                key: Key to press (e.g., 'Enter', 'Tab', 'Control+a', 'Meta+c')
                delay: Delay between key events
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                if selector:
                    page.press(selector, key, delay=delay)
                else:
                    page.keyboard.press(key, delay=delay)

                return {
                    "success": True,
                    "key": key
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def select_option(
            selector: str,
            value: Optional[str] = None,
            label: Optional[str] = None,
            index: Optional[int] = None,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Select an option from a dropdown.

            Args:
                selector: CSS selector for select element
                value: Option value to select
                label: Option label to select
                index: Option index to select
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                option = None
                if value is not None:
                    option = value
                elif label is not None:
                    option = {"label": label}
                elif index is not None:
                    option = {"index": index}

                page.select_option(selector, option, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector,
                    "selected": option
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def check_checkbox(
            selector: str,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Check a checkbox or radio button."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.check(selector, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector,
                    "checked": True
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def uncheck_checkbox(
            selector: str,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Uncheck a checkbox."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.uncheck(selector, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector,
                    "checked": False
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def upload_file(
            selector: str,
            file_path: str,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Upload a file to a file input."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.set_input_files(selector, file_path, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "selector": selector,
                    "file": file_path
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def scroll(
            direction: str = "down",
            amount: int = 500,
            selector: Optional[str] = None
        ) -> Dict[str, Any]:
            """Scroll the page or an element.

            Args:
                direction: Scroll direction (up, down, left, right)
                amount: Scroll amount in pixels
                selector: CSS selector for element scroll (optional)
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                if selector:
                    element = page.query_selector(selector)
                    if element:
                        if direction == "down":
                            element.evaluate(f"el => el.scrollTop += {amount}")
                        elif direction == "up":
                            element.evaluate(f"el => el.scrollTop -= {amount}")
                        elif direction == "right":
                            element.evaluate(f"el => el.scrollLeft += {amount}")
                        elif direction == "left":
                            element.evaluate(f"el => el.scrollLeft -= {amount}")
                else:
                    if direction == "down":
                        page.mouse.wheel(0, amount)
                    elif direction == "up":
                        page.mouse.wheel(0, -amount)
                    elif direction == "right":
                        page.mouse.wheel(amount, 0)
                    elif direction == "left":
                        page.mouse.wheel(-amount, 0)

                return {
                    "success": True,
                    "direction": direction,
                    "amount": amount
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_form_tools(self):
        """Register form-related tools."""

        @self.mcp_server.tool()
        def fill_form(
            fields: Dict[str, str],
            submit_selector: Optional[str] = None,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Fill multiple form fields at once.

            Args:
                fields: Dictionary of selector -> value pairs
                submit_selector: Selector for submit button (optional)
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                filled = []
                for selector, value in fields.items():
                    try:
                        page.fill(selector, value, timeout=timeout or self.timeout)
                        filled.append(selector)
                    except Exception as e:
                        return {
                            "success": False,
                            "filled": filled,
                            "failed": selector,
                            "error": str(e)
                        }

                if submit_selector:
                    page.click(submit_selector, timeout=timeout or self.timeout)

                return {
                    "success": True,
                    "filled_count": len(filled),
                    "fields_filled": filled,
                    "submitted": submit_selector is not None
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_form_data(
            form_selector: str
        ) -> Dict[str, Any]:
            """Extract all form field data."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                form_data = page.evaluate(f"""
                    () => {{
                        const form = document.querySelector('{form_selector}');
                        if (!form) return null;

                        const formData = new FormData(form);
                        const data = {{}};
                        for (let [key, value] of formData.entries()) {{
                            data[key] = value;
                        }}
                        return data;
                    }}
                """)

                return {
                    "success": True,
                    "form_selector": form_selector,
                    "data": form_data or {}
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def analyze_form(
            form_selector: str
        ) -> Dict[str, Any]:
            """Analyze a form and return field information."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                fields_info = page.evaluate(f"""
                    () => {{
                        const form = document.querySelector('{form_selector}');
                        if (!form) return null;

                        const fields = [];
                        const inputs = form.querySelectorAll('input, select, textarea');

                        inputs.forEach(input => {{
                            fields.push({{
                                tag: input.tagName.toLowerCase(),
                                type: input.type || input.tagName.toLowerCase(),
                                name: input.name,
                                id: input.id,
                                placeholder: input.placeholder,
                                required: input.required,
                                value: input.value,
                                label: input.labels ? (input.labels[0]?.textContent || null) : null
                            }});
                        }});

                        return fields;
                    }}
                """)

                return {
                    "success": True,
                    "form_selector": form_selector,
                    "fields_count": len(fields_info) if fields_info else 0,
                    "fields": fields_info or []
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_extraction_tools(self):
        """Register data extraction tools."""

        @self.mcp_server.tool()
        def get_text(selector: str) -> Dict[str, Any]:
            """Get text content of an element."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                text = page.text_content(selector)

                return {
                    "success": True,
                    "selector": selector,
                    "text": text
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_attribute(
            selector: str,
            attribute: str
        ) -> Dict[str, Any]:
            """Get an attribute value from an element."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                value = page.get_attribute(selector, attribute)

                return {
                    "success": True,
                    "selector": selector,
                    "attribute": attribute,
                    "value": value
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_inner_html(selector: str) -> Dict[str, Any]:
            """Get inner HTML of an element."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                html = page.inner_html(selector)

                return {
                    "success": True,
                    "selector": selector,
                    "html": html
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def query_selector_all(
            selector: str
        ) -> Dict[str, Any]:
            """Query all matching elements and return their information."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                elements = page.query_selector_all(selector)
                results = []

                for i, element in enumerate(elements):
                    try:
                        box = element.bounding_box()
                        results.append({
                            "index": i,
                            "text": element.text_content(),
                            "tag": element.evaluate("el => el.tagName.toLowerCase()"),
                            "visible": element.is_visible(),
                            "bounding_box": box
                        })
                    except:
                        pass

                return {
                    "success": True,
                    "selector": selector,
                    "count": len(results),
                    "elements": results
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def extract_table(
            selector: str = "table",
            include_headers: bool = True
        ) -> Dict[str, Any]:
            """Extract data from an HTML table."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                table_data = page.evaluate(f"""
                    () => {{
                        const table = document.querySelector('{selector}');
                        if (!table) return null;

                        const rows = table.querySelectorAll('tr');
                        const data = [];

                        rows.forEach((row, index) => {{
                            const cells = row.querySelectorAll('td, th');
                            const rowData = [];
                            cells.forEach(cell => rowData.push(cell.textContent.trim()));
                            if (rowData.length > 0) {{
                                data.push(rowData);
                            }}
                        }});

                        return data;
                    }}
                """)

                headers = []
                if include_headers and table_data:
                    headers = table_data[0]
                    table_data = table_data[1:] if len(table_data) > 1 else []

                return {
                    "success": True,
                    "selector": selector,
                    "headers": headers,
                    "rows": table_data or [],
                    "row_count": len(table_data) if table_data else 0
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_page_content() -> Dict[str, Any]:
            """Get the full page HTML content."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                content = page.content()

                return {
                    "success": True,
                    "url": page.url,
                    "title": page.title(),
                    "content_length": len(content),
                    "content": content[:50000]  # Limit size
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def execute_javascript(
            script: str,
            arg: Optional[Any] = None
        ) -> Dict[str, Any]:
            """Execute JavaScript in the browser context.

            Args:
                script: JavaScript code to execute
                arg: Optional argument to pass to the script
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                result = page.evaluate(script, arg)

                return {
                    "success": True,
                    "result": result
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_screenshot_tools(self):
        """Register screenshot and visual tools."""

        @self.mcp_server.tool()
        def take_screenshot(
            path: Optional[str] = None,
            selector: Optional[str] = None,
            full_page: bool = False,
            format: str = "png",
            quality: Optional[int] = None
        ) -> Dict[str, Any]:
            """Take a screenshot of the page or element.

            Args:
                path: File path to save screenshot (optional)
                selector: CSS selector for element screenshot
                full_page: Capture full scrollable page
                format: Image format (png, jpeg)
                quality: JPEG quality (1-100)
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                screenshot_options = {
                    "type": format,
                    "full_page": full_page
                }

                if quality and format == "jpeg":
                    screenshot_options["quality"] = quality

                if path:
                    screenshot_options["path"] = path

                if selector:
                    element = page.query_selector(selector)
                    if element:
                        screenshot_bytes = element.screenshot(**screenshot_options)
                    else:
                        return {"error": f"Element not found: {selector}"}
                else:
                    screenshot_bytes = page.screenshot(**screenshot_options)

                # Encode to base64 if not saving to file
                if not path:
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                else:
                    screenshot_base64 = None

                return {
                    "success": True,
                    "path": path,
                    "format": format,
                    "full_page": full_page,
                    "selector": selector,
                    "size_bytes": len(screenshot_bytes) if screenshot_bytes else 0,
                    "base64": screenshot_base64[:1000] + "..." if screenshot_base64 and len(screenshot_base64) > 1000 else screenshot_base64
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def generate_pdf(
            path: Optional[str] = None,
            format: str = "A4",
            landscape: bool = False,
            margin_top: str = "1cm",
            margin_bottom: str = "1cm",
            margin_left: str = "1cm",
            margin_right: str = "1cm",
            print_background: bool = True
        ) -> Dict[str, Any]:
            """Generate PDF from the current page.

            Args:
                path: File path to save PDF
                format: Paper format (A4, Letter, etc.)
                landscape: Landscape orientation
                margin_*: Page margins
                print_background: Print background graphics
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                pdf_options = {
                    "format": format,
                    "landscape": landscape,
                    "print_background": print_background,
                    "margin": {
                        "top": margin_top,
                        "bottom": margin_bottom,
                        "left": margin_left,
                        "right": margin_right
                    }
                }

                if path:
                    pdf_options["path"] = path

                pdf_bytes = page.pdf(**pdf_options)

                return {
                    "success": True,
                    "path": path,
                    "format": format,
                    "size_bytes": len(pdf_bytes),
                    "base64": base64.b64encode(pdf_bytes).decode('utf-8')[:500] + "..."
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def wait_for_selector(
            selector: str,
            state: str = "visible",
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Wait for an element to appear.

            Args:
                selector: CSS selector
                state: Element state to wait for (visible, hidden, attached, detached)
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.wait_for_selector(
                    selector,
                    state=state,
                    timeout=timeout or self.timeout
                )

                return {
                    "success": True,
                    "selector": selector,
                    "state": state
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def wait_for_navigation(
            timeout: Optional[int] = None,
            wait_until: str = "load"
        ) -> Dict[str, Any]:
            """Wait for navigation to complete."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                with page.expect_navigation(timeout=timeout or self.timeout, wait_until=wait_until):
                    pass

                return {
                    "success": True,
                    "url": page.url,
                    "title": page.title()
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_network_tools(self):
        """Register network-related tools."""

        @self.mcp_server.tool()
        def get_cookies(urls: Optional[List[str]] = None) -> Dict[str, Any]:
            """Get browser cookies.

            Args:
                urls: URLs to get cookies for (optional)
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                instance = self._instances.get(self._active_session)
                context = instance["context"] if instance else None

                if context is None:
                    return {"error": "No browser context available"}

                cookies = context.cookies(urls)

                return {
                    "success": True,
                    "count": len(cookies),
                    "cookies": cookies
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def set_cookies(cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
            """Set browser cookies.

            Args:
                cookies: List of cookie objects with name, value, domain, etc.
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                instance = self._instances.get(self._active_session)
                context = instance["context"] if instance else None

                if context is None:
                    return {"error": "No browser context available"}

                context.add_cookies(cookies)

                return {
                    "success": True,
                    "count": len(cookies),
                    "message": f"Added {len(cookies)} cookies"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def clear_cookies() -> Dict[str, Any]:
            """Clear all browser cookies."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                instance = self._instances.get(self._active_session)
                context = instance["context"] if instance else None

                if context is None:
                    return {"error": "No browser context available"}

                context.clear_cookies()

                return {
                    "success": True,
                    "message": "All cookies cleared"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_local_storage() -> Dict[str, Any]:
            """Get local storage data."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                storage = page.evaluate("""
                    () => {
                        const data = {};
                        for (let i = 0; i < localStorage.length; i++) {
                            const key = localStorage.key(i);
                            data[key] = localStorage.getItem(key);
                        }
                        return data;
                    }
                """)

                return {
                    "success": True,
                    "count": len(storage),
                    "data": storage
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def set_local_storage(data: Dict[str, str]) -> Dict[str, Any]:
            """Set local storage data."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.evaluate(f"""
                    (data) => {{
                        Object.entries(data).forEach(([key, value]) => {{
                            localStorage.setItem(key, value);
                        }});
                    }}
                """, data)

                return {
                    "success": True,
                    "count": len(data),
                    "message": f"Set {len(data)} local storage items"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def intercept_requests(
            url_pattern: str,
            action: str = "block"
        ) -> Dict[str, Any]:
            """Intercept and modify network requests.

            Args:
                url_pattern: URL pattern to intercept (supports wildcards)
                action: Action to take (block, abort, continue)
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                def handle_route(route):
                    if action == "block":
                        route.abort()
                    else:
                        route.continue_()

                page.route(url_pattern, handle_route)

                return {
                    "success": True,
                    "pattern": url_pattern,
                    "action": action,
                    "message": f"Request interception configured for {url_pattern}"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def mock_api_response(
            url_pattern: str,
            response_body: Any,
            status: int = 200,
            headers: Optional[Dict[str, str]] = None
        ) -> Dict[str, Any]:
            """Mock API responses for testing.

            Args:
                url_pattern: URL pattern to mock
                response_body: Response body (will be JSON encoded)
                status: HTTP status code
                headers: Response headers
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                def handle_route(route):
                    route.fulfill(
                        status=status,
                        headers=headers or {"Content-Type": "application/json"},
                        body=json.dumps(response_body) if isinstance(response_body, dict) else str(response_body)
                    )

                page.route(url_pattern, handle_route)

                return {
                    "success": True,
                    "pattern": url_pattern,
                    "status": status,
                    "message": f"Mocking responses for {url_pattern}"
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_advanced_tools(self):
        """Register advanced browser automation tools."""

        @self.mcp_server.tool()
        def handle_dialog(
            accept: bool = True,
            prompt_text: Optional[str] = None
        ) -> Dict[str, Any]:
            """Handle JavaScript dialogs (alert, confirm, prompt).

            Args:
                accept: Accept or dismiss the dialog
                prompt_text: Text to enter for prompt dialogs
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                def on_dialog(dialog):
                    if prompt_text and dialog.type == "prompt":
                        dialog.accept(prompt_text)
                    elif accept:
                        dialog.accept()
                    else:
                        dialog.dismiss()

                page.on("dialog", on_dialog)

                return {
                    "success": True,
                    "message": "Dialog handler registered"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def emulate_device(
            device_name: str
        ) -> Dict[str, Any]:
            """Emulate a mobile device.

            Args:
                device_name: Device name (e.g., 'iPhone 13', 'Galaxy S5', 'iPad Pro')
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                # Get device from playwright devices
                sync_playwright = _import_playwright()
                playwright = self._playwright_context

                if playwright is None:
                    return {"error": "Playwright not initialized"}

                # Get device settings
                device = playwright.devices.get(device_name)
                if device is None:
                    return {"error": f"Device {device_name} not found. Available devices: {list(playwright.devices.keys())[:10]}..."}

                # Apply device settings
                instance = self._instances.get(self._active_session)
                if instance:
                    new_context = instance["browser"].new_context(**device)
                    new_page = new_context.new_page()

                    # Update instance
                    instance["context"].close()
                    instance["context"] = new_context
                    instance["page"] = new_page

                return {
                    "success": True,
                    "device": device_name,
                    "viewport": device.get("viewport"),
                    "user_agent": device.get("user_agent")
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def set_geolocation(
            latitude: float,
            longitude: float,
            accuracy: Optional[float] = None
        ) -> Dict[str, Any]:
            """Set geolocation for the browser.

            Args:
                latitude: Latitude coordinate
                longitude: Longitude coordinate
                accuracy: Accuracy in meters
            """
            try:
                instance = self._instances.get(self._active_session)
                if instance is None:
                    return {"error": "No active browser session"}

                context = instance["context"]
                context.set_geolocation({
                    "latitude": latitude,
                    "longitude": longitude,
                    "accuracy": accuracy
                })

                return {
                    "success": True,
                    "latitude": latitude,
                    "longitude": longitude
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def set_viewport_size(
            width: int,
            height: int
        ) -> Dict[str, Any]:
            """Set the viewport size."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                page.set_viewport_size({"width": width, "height": height})

                return {
                    "success": True,
                    "width": width,
                    "height": height
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def drag_and_drop(
            source_selector: str,
            target_selector: str,
            steps: int = 10
        ) -> Dict[str, Any]:
            """Perform drag and drop operation."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                source = page.query_selector(source_selector)
                target = page.query_selector(target_selector)

                if not source:
                    return {"error": f"Source element not found: {source_selector}"}
                if not target:
                    return {"error": f"Target element not found: {target_selector}"}

                source.drag_to(target, steps=steps)

                return {
                    "success": True,
                    "source": source_selector,
                    "target": target_selector
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def new_page(url: Optional[str] = None) -> Dict[str, Any]:
            """Open a new page/tab."""
            try:
                instance = self._instances.get(self._active_session)
                if instance is None:
                    return {"error": "No active browser session"}

                context = instance["context"]
                new_page = context.new_page()

                if url:
                    new_page.goto(url)

                return {
                    "success": True,
                    "page_count": len(context.pages),
                    "url": new_page.url
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def switch_page(index: int) -> Dict[str, Any]:
            """Switch to a different page/tab."""
            try:
                instance = self._instances.get(self._active_session)
                if instance is None:
                    return {"error": "No active browser session"}

                context = instance["context"]
                pages = context.pages

                if index < 0 or index >= len(pages):
                    return {"error": f"Invalid page index: {index}. Pages: {len(pages)}"}

                instance["page"] = pages[index]

                return {
                    "success": True,
                    "page_index": index,
                    "url": pages[index].url,
                    "title": pages[index].title()
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def close_page(index: Optional[int] = None) -> Dict[str, Any]:
            """Close a page/tab."""
            try:
                instance = self._instances.get(self._active_session)
                if instance is None:
                    return {"error": "No active browser session"}

                context = instance["context"]
                pages = context.pages

                if len(pages) == 1:
                    return {"error": "Cannot close the last page"}

                target_index = index if index is not None else len(pages) - 1
                if target_index < 0 or target_index >= len(pages):
                    return {"error": f"Invalid page index: {target_index}"}

                pages[target_index].close()

                # Update active page if needed
                if instance["page"] == pages[target_index]:
                    instance["page"] = context.pages[0]

                return {
                    "success": True,
                    "remaining_pages": len(context.pages)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def download_file(
            trigger_selector: str,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Trigger and wait for a file download.

            Args:
                trigger_selector: Selector for the download trigger element
            """
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                with page.expect_download(timeout=timeout or self.timeout * 2) as download_info:
                    page.click(trigger_selector)

                download = download_info.value

                # Save download
                save_path = os.path.join(self.downloads_path, download.suggested_filename)
                download.save_as(save_path)

                return {
                    "success": True,
                    "filename": download.suggested_filename,
                    "save_path": save_path,
                    "url": download.url
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def wait_for_popup() -> Dict[str, Any]:
            """Wait for a popup window and return its info."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                with page.expect_popup() as popup_info:
                    pass  # User should trigger popup before calling this

                popup = popup_info.value

                return {
                    "success": True,
                    "url": popup.url,
                    "title": popup.title()
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_console_logs() -> Dict[str, Any]:
            """Get console logs from the browser."""
            try:
                instance = self._instances.get(self._active_session)
                if instance is None:
                    return {"error": "No active browser session"}

                # This would need to be set up before navigation
                # For now, return instruction
                return {
                    "success": True,
                    "message": "Console log capture needs to be configured before page navigation",
                    "instruction": "Use listen_console_events tool first"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def listen_console_events() -> Dict[str, Any]:
            """Start listening to console events."""
            try:
                page = self._get_active_page()
                if page is None:
                    return {"error": "No active browser session"}

                console_messages = []

                def on_console(msg):
                    console_messages.append({
                        "type": msg.type,
                        "text": msg.text,
                        "location": msg.location
                    })

                page.on("console", on_console)

                # Store for later retrieval
                instance = self._instances.get(self._active_session)
                if instance:
                    instance["console_messages"] = console_messages

                return {
                    "success": True,
                    "message": "Console event listener started"
                }
            except Exception as e:
                return {"error": str(e)}


def main():
    """Main entry point for the Browser Automation MCP Server."""
    import argparse

    parser = argparse.ArgumentParser(description="Browser Automation MCP Server")
    parser.add_argument(
        "--browser",
        type=str,
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser type to use"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser with GUI"
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1920,
        help="Viewport width"
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1080,
        help="Viewport height"
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol"
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    server = BrowserMCPServer(
        browser_type=BrowserType(args.browser),
        headless=not args.no_headless,
        viewport_width=args.viewport_width,
        viewport_height=args.viewport_height,
        transport=args.transport,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    print(f"Starting Browser Automation MCP Server")
    print(f"Browser: {args.browser}")
    print(f"Headless: {args.headless}")
    print(f"Transport: {args.transport}")

    server.run()


if __name__ == "__main__":
    main()