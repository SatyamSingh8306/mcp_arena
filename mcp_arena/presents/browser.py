"""
Browser Automation MCP Server
A comprehensive browser automation server using Playwright for web automation,
scraping, testing, and more.
"""
import os
import asyncio
import json
import base64
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict

from mcp_arena.mcp.server import BaseMCPServer

try:
    from playwright.async_api import async_playwright as _async_playwright
except ImportError:
    _async_playwright = None


def _ensure_playwright():
    if _async_playwright is None:
        raise ImportError("playwright is required. pip install playwright && playwright install")
    return _async_playwright


class BrowserSession(TypedDict, total=False):
    session_id: str
    browser_type: str
    headless: bool
    viewport_width: int
    viewport_height: int
    user_agent: Optional[str]
    created_at: str
    current_url: Optional[str]
    current_title: Optional[str]
    pages_count: int
    is_active: bool


class BrowserMCPServer(BaseMCPServer):
    """Browser Automation MCP Server using Playwright (async API)."""
    _REQUIRED_EXTRAS = {"PIL": "browser", "cv2": "browser", "playwright": "browser"}

    _instances: Dict[str, Any] = {}
    _pw = None  # async playwright instance
    _active_session: Optional[str] = None

    def __init__(
        self,
        browser_type: str = "chromium",
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
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
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

        Path(self.downloads_path).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="Browser Automation MCP Server",
            description="MCP server for browser automation using Playwright",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    # ------------------------------------------------------------------
    # Internal helpers (all async now)
    # ------------------------------------------------------------------

    async def _ensure_playwright(self):
        """Start the async playwright process exactly once."""
        if self._pw is None:
            playwright = _ensure_playwright()
            self.__class__._pw_cm = playwright()
            self.__class__._pw = await self.__class__._pw_cm.__aenter__()
        return self._pw

    async def _create_session(
        self,
        browser_type: str = None,
        headless: bool = None,
        viewport_width: int = None,
        viewport_height: int = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Create a new browser session asynchronously."""
        pw = await self._ensure_playwright()

        bt = browser_type or self.browser_type
        hl = headless if headless is not None else self.headless
        vw = viewport_width or self.viewport_width
        vh = viewport_height or self.viewport_height
        ua = user_agent or self.user_agent

        launcher = getattr(pw, bt)

        launch_opts: Dict[str, Any] = {
            "headless": hl,
            "slow_mo": self.slow_mo,
            "downloads_path": self.downloads_path,
        }
        if self.proxy:
            launch_opts["proxy"] = self.proxy

        browser = await launcher.launch(**launch_opts)

        ctx_opts: Dict[str, Any] = {
            "viewport": {"width": vw, "height": vh},
            "ignore_https_errors": self.ignore_https_errors,
        }
        if ua:
            ctx_opts["user_agent"] = ua

        context = await browser.new_context(**ctx_opts)
        context.set_default_timeout(self.timeout)
        page = await context.new_page()

        session_id = str(uuid.uuid4())[:8]
        instance = {
            "browser": browser,
            "context": context,
            "page": page,
            "console_messages": [],
            "info": BrowserSession(
                session_id=session_id,
                browser_type=bt,
                headless=hl,
                viewport_width=vw,
                viewport_height=vh,
                user_agent=ua,
                created_at=datetime.now().isoformat(),
            ),
        }
        self._instances[session_id] = instance

        if self._active_session is None:
            self.__class__._active_session = session_id

        return instance

    async def _get_or_create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        if session_id and session_id in self._instances:
            return self._instances[session_id]
        if self._active_session and self._active_session in self._instances:
            return self._instances[self._active_session]
        return await self._create_session()

    async def _active_page(self):
        inst = await self._get_or_create_session()
        return inst["page"]

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        self._register_session_tools()
        self._register_navigation_tools()
        self._register_interaction_tools()
        self._register_form_tools()
        self._register_extraction_tools()
        self._register_screenshot_tools()
        self._register_network_tools()
        self._register_advanced_tools()

    # ---- Session tools -----------------------------------------------

    def _register_session_tools(self):

        @self.mcp_server.tool()
        async def create_browser_session(
            browser_type: str = "chromium",
            headless: bool = True,
            viewport_width: int = 1920,
            viewport_height: int = 1080,
            user_agent: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Create a new browser session.

            Args:
                browser_type: chromium | firefox | webkit
                headless: Run headless
                viewport_width: Viewport width in pixels
                viewport_height: Viewport height in pixels
                user_agent: Custom user-agent string
            """
            try:
                inst = await self._create_session(
                    browser_type=browser_type,
                    headless=headless,
                    viewport_width=viewport_width,
                    viewport_height=viewport_height,
                    user_agent=user_agent,
                )
                return {"success": True, "session": dict(inst["info"])}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def list_browser_sessions() -> Dict[str, Any]:
            """List all active browser sessions."""
            try:
                sessions = []
                for sid, inst in self._instances.items():
                    info = inst["info"]
                    try:
                        info.current_url = inst["page"].url
                        info.current_title = await inst["page"].title()
                        info.pages_count = len(inst["context"].pages)
                    except Exception:
                        pass
                    sessions.append(dict(info))
                return {
                    "count": len(sessions),
                    "active_session": self._active_session,
                    "sessions": sessions,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def switch_session(session_id: str) -> Dict[str, Any]:
            """Switch the active browser session."""
            try:
                if session_id not in self._instances:
                    return {"error": f"Session {session_id} not found"}
                self.__class__._active_session = session_id
                inst = self._instances[session_id]
                return {
                    "success": True,
                    "active_session": session_id,
                    "current_url": inst["page"].url,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def close_browser_session(session_id: Optional[str] = None) -> Dict[str, Any]:
            """Close a browser session."""
            try:
                target = session_id or self._active_session
                if not target:
                    return {"error": "No active session to close"}
                if target not in self._instances:
                    return {"error": f"Session {target} not found"}

                inst = self._instances[target]
                await inst["context"].close()
                await inst["browser"].close()
                del self._instances[target]

                if self._active_session == target:
                    self.__class__._active_session = next(iter(self._instances), None)

                return {
                    "success": True,
                    "message": f"Session {target} closed",
                    "remaining_sessions": list(self._instances.keys()),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def close_all_sessions() -> Dict[str, Any]:
            """Close all browser sessions."""
            try:
                closed = []
                for sid in list(self._instances.keys()):
                    inst = self._instances[sid]
                    try:
                        await inst["context"].close()
                        await inst["browser"].close()
                        closed.append(sid)
                    except Exception:
                        pass
                self._instances.clear()
                self.__class__._active_session = None

                if self._pw is not None:
                    try:
                        await self.__class__._pw_cm.__aexit__(None, None, None)
                    except Exception:
                        pass
                    self.__class__._pw = None

                return {"success": True, "closed_sessions": closed}
            except Exception as e:
                return {"error": str(e)}

    # ---- Navigation tools --------------------------------------------

    def _register_navigation_tools(self):

        @self.mcp_server.tool()
        async def navigate(
            url: str,
            wait_until: str = "load",
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Navigate to a URL.

            Args:
                url: Destination URL
                wait_until: load | domcontentloaded | networkidle
                timeout: Milliseconds before timeout
            """
            try:
                page = await self._active_page()
                resp = await page.goto(
                    url, wait_until=wait_until, timeout=timeout or self.timeout
                )
                return {
                    "success": True,
                    "url": page.url,
                    "title": await page.title(),
                    "status": resp.status if resp else None,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def go_back(timeout: Optional[int] = None) -> Dict[str, Any]:
            """Go back in browser history."""
            try:
                page = await self._active_page()
                await page.go_back(timeout=timeout or self.timeout)
                return {"success": True, "url": page.url, "title": await page.title()}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def go_forward(timeout: Optional[int] = None) -> Dict[str, Any]:
            """Go forward in browser history."""
            try:
                page = await self._active_page()
                await page.go_forward(timeout=timeout or self.timeout)
                return {"success": True, "url": page.url, "title": await page.title()}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def refresh(timeout: Optional[int] = None) -> Dict[str, Any]:
            """Reload the current page."""
            try:
                page = await self._active_page()
                await page.reload(timeout=timeout or self.timeout)
                return {"success": True, "url": page.url, "title": await page.title()}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def get_current_url() -> Dict[str, Any]:
            """Return current page URL and title."""
            try:
                page = await self._active_page()
                return {"url": page.url, "title": await page.title()}
            except Exception as e:
                return {"error": str(e)}

    # ---- Interaction tools -------------------------------------------

    def _register_interaction_tools(self):

        @self.mcp_server.tool()
        async def click(
            selector: str,
            button: str = "left",
            click_count: int = 1,
            delay: int = 0,
            force: bool = False,
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Click an element.

            Args:
                selector: CSS selector or XPath
                button: left | right | middle
                click_count: 1 = single click, 2 = double click
                delay: ms between mousedown and mouseup
                force: Skip actionability checks
                timeout: Milliseconds before timeout
            """
            try:
                page = await self._active_page()
                await page.click(
                    selector,
                    button=button,
                    click_count=click_count,
                    delay=delay,
                    force=force,
                    timeout=timeout or self.timeout,
                )
                return {"success": True, "selector": selector}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def double_click(
            selector: str, timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Double-click an element."""
            try:
                page = await self._active_page()
                await page.dblclick(selector, timeout=timeout or self.timeout)
                return {"success": True, "selector": selector}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def hover(
            selector: str, timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Hover over an element."""
            try:
                page = await self._active_page()
                await page.hover(selector, timeout=timeout or self.timeout)
                return {"success": True, "selector": selector}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def type_text(
            selector: str,
            text: str,
            delay: int = 0,
            clear: bool = True,
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Type text into an input field.

            Args:
                selector: CSS selector for the input
                text: Text to type
                delay: ms between keystrokes
                clear: Clear field first
                timeout: Milliseconds before timeout
            """
            try:
                page = await self._active_page()
                if clear:
                    await page.fill(selector, "", timeout=timeout or self.timeout)
                await page.type(
                    selector, text, delay=delay, timeout=timeout or self.timeout
                )
                return {
                    "success": True,
                    "selector": selector,
                    "text_length": len(text),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def fill_input(
            selector: str,
            value: str,
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Fill an input field instantly (faster than type_text)."""
            try:
                page = await self._active_page()
                await page.fill(selector, value, timeout=timeout or self.timeout)
                return {"success": True, "selector": selector}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def press_key(
            key: str,
            selector: Optional[str] = None,
            delay: int = 0,
        ) -> Dict[str, Any]:
            """Press a key or key combination.

            Args:
                key: e.g. 'Enter', 'Tab', 'Control+a'
                selector: Focus this element first (optional)
                delay: ms between key events
            """
            try:
                page = await self._active_page()
                if selector:
                    await page.press(selector, key, delay=delay)
                else:
                    await page.keyboard.press(key, delay=delay)
                return {"success": True, "key": key}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def select_option(
            selector: str,
            value: Optional[str] = None,
            label: Optional[str] = None,
            index: Optional[int] = None,
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Select a dropdown option by value, label, or index."""
            try:
                page = await self._active_page()
                if value is not None:
                    opt: Any = value
                elif label is not None:
                    opt = {"label": label}
                elif index is not None:
                    opt = {"index": index}
                else:
                    return {"error": "Provide value, label, or index"}
                await page.select_option(
                    selector, opt, timeout=timeout or self.timeout
                )
                return {"success": True, "selector": selector, "selected": opt}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def check_checkbox(
            selector: str, timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Check a checkbox or radio button."""
            try:
                page = await self._active_page()
                await page.check(selector, timeout=timeout or self.timeout)
                return {"success": True, "selector": selector, "checked": True}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def uncheck_checkbox(
            selector: str, timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Uncheck a checkbox."""
            try:
                page = await self._active_page()
                await page.uncheck(selector, timeout=timeout or self.timeout)
                return {"success": True, "selector": selector, "checked": False}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def upload_file(
            selector: str,
            file_path: str,
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Upload a file via a file input element."""
            try:
                page = await self._active_page()
                await page.set_input_files(
                    selector, file_path, timeout=timeout or self.timeout
                )
                return {"success": True, "selector": selector, "file": file_path}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def scroll(
            direction: str = "down",
            amount: int = 500,
            selector: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Scroll the page or a specific element.

            Args:
                direction: up | down | left | right
                amount: Pixels to scroll
                selector: Scroll inside this element (optional)
            """
            try:
                page = await self._active_page()
                dx = {"right": amount, "left": -amount}.get(direction, 0)
                dy = {"down": amount, "up": -amount}.get(direction, 0)

                if selector:
                    el = await page.query_selector(selector)
                    if el:
                        await el.evaluate(
                            f"(el) => {{ el.scrollLeft += {dx}; el.scrollTop += {dy}; }}"
                        )
                    else:
                        return {"error": f"Element not found: {selector}"}
                else:
                    await page.mouse.wheel(dx, dy)

                return {"success": True, "direction": direction, "amount": amount}
            except Exception as e:
                return {"error": str(e)}

    # ---- Form tools --------------------------------------------------

    def _register_form_tools(self):

        @self.mcp_server.tool()
        async def fill_form(
            fields: Dict[str, str],
            submit_selector: Optional[str] = None,
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Fill multiple form fields at once.

            Args:
                fields: {css_selector: value, ...}
                submit_selector: Click this after filling (optional)
                timeout: Milliseconds before timeout
            """
            try:
                page = await self._active_page()
                filled = []
                for sel, val in fields.items():
                    await page.fill(sel, val, timeout=timeout or self.timeout)
                    filled.append(sel)
                if submit_selector:
                    await page.click(
                        submit_selector, timeout=timeout or self.timeout
                    )
                return {
                    "success": True,
                    "filled_count": len(filled),
                    "submitted": submit_selector is not None,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def analyze_form(form_selector: str) -> Dict[str, Any]:
            """Inspect a form and return its field definitions."""
            try:
                page = await self._active_page()
                fields = await page.evaluate(
                    """(sel) => {
                        const form = document.querySelector(sel);
                        if (!form) return null;
                        return Array.from(form.querySelectorAll('input,select,textarea')).map(el => ({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || el.tagName.toLowerCase(),
                            name: el.name,
                            id: el.id,
                            placeholder: el.placeholder || null,
                            required: el.required,
                            value: el.value,
                            label: el.labels && el.labels[0] ? el.labels[0].textContent.trim() : null
                        }));
                    }""",
                    form_selector,
                )
                return {
                    "success": True,
                    "form_selector": form_selector,
                    "fields_count": len(fields) if fields else 0,
                    "fields": fields or [],
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def get_form_data(form_selector: str) -> Dict[str, Any]:
            """Extract current values from all form fields."""
            try:
                page = await self._active_page()
                data = await page.evaluate(
                    """(sel) => {
                        const form = document.querySelector(sel);
                        if (!form) return null;
                        const fd = new FormData(form);
                        const out = {};
                        for (const [k, v] of fd.entries()) out[k] = v;
                        return out;
                    }""",
                    form_selector,
                )
                return {"success": True, "data": data or {}}
            except Exception as e:
                return {"error": str(e)}

    # ---- Extraction tools --------------------------------------------

    def _register_extraction_tools(self):

        @self.mcp_server.tool()
        async def get_text(selector: str) -> Dict[str, Any]:
            """Get the text content of an element."""
            try:
                page = await self._active_page()
                return {
                    "success": True,
                    "selector": selector,
                    "text": await page.text_content(selector),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def get_attribute(selector: str, attribute: str) -> Dict[str, Any]:
            """Get an attribute value from an element."""
            try:
                page = await self._active_page()
                return {
                    "success": True,
                    "selector": selector,
                    "attribute": attribute,
                    "value": await page.get_attribute(selector, attribute),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def get_inner_html(selector: str) -> Dict[str, Any]:
            """Get the inner HTML of an element."""
            try:
                page = await self._active_page()
                return {
                    "success": True,
                    "selector": selector,
                    "html": await page.inner_html(selector),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def query_selector_all(selector: str) -> Dict[str, Any]:
            """Query all matching elements and return info about each."""
            try:
                page = await self._active_page()
                elements = await page.query_selector_all(selector)
                results = []
                for i, el in enumerate(elements):
                    try:
                        results.append(
                            {
                                "index": i,
                                "text": await el.text_content(),
                                "tag": await el.evaluate(
                                    "el => el.tagName.toLowerCase()"
                                ),
                                "visible": await el.is_visible(),
                                "bounding_box": await el.bounding_box(),
                            }
                        )
                    except Exception:
                        pass
                return {
                    "success": True,
                    "selector": selector,
                    "count": len(results),
                    "elements": results,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def extract_table(
            selector: str = "table",
            include_headers: bool = True,
        ) -> Dict[str, Any]:
            """Extract data from an HTML table."""
            try:
                page = await self._active_page()
                raw = await page.evaluate(
                    """(sel) => {
                        const t = document.querySelector(sel);
                        if (!t) return null;
                        return Array.from(t.querySelectorAll('tr')).map(r =>
                            Array.from(r.querySelectorAll('td,th')).map(c => c.textContent.trim())
                        ).filter(r => r.length);
                    }""",
                    selector,
                )
                headers: List[str] = []
                rows = raw or []
                if include_headers and rows:
                    headers = rows[0]
                    rows = rows[1:]
                return {
                    "success": True,
                    "selector": selector,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def get_page_content() -> Dict[str, Any]:
            """Return the full page HTML (capped at 50 000 chars)."""
            try:
                page = await self._active_page()
                content = await page.content()
                return {
                    "success": True,
                    "url": page.url,
                    "title": await page.title(),
                    "content_length": len(content),
                    "content": content[:50000],
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def execute_javascript(
            script: str, arg: Optional[Any] = None
        ) -> Dict[str, Any]:
            """Execute JavaScript in the page context.

            Args:
                script: JS expression or function, e.g. '() => document.title'
                arg: Optional serialisable argument passed to the function
            """
            try:
                page = await self._active_page()
                if arg is not None:
                    result = await page.evaluate(script, arg)
                else:
                    result = await page.evaluate(script)
                return {"success": True, "result": result}
            except Exception as e:
                return {"error": str(e)}

    # ---- Screenshot / PDF tools -------------------------------------

    def _register_screenshot_tools(self):

        @self.mcp_server.tool()
        async def take_screenshot(
            path: Optional[str] = None,
            selector: Optional[str] = None,
            full_page: bool = False,
            format: str = "png",
            quality: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Capture a screenshot.

            Args:
                path: Save to this file path (optional)
                selector: Capture only this element (optional)
                full_page: Capture full scrollable page
                format: png | jpeg
                quality: JPEG quality 1-100
            """
            try:
                page = await self._active_page()
                opts: Dict[str, Any] = {"type": format, "full_page": full_page}
                if path:
                    opts["path"] = path
                if quality and format == "jpeg":
                    opts["quality"] = quality

                if selector:
                    el = await page.query_selector(selector)
                    if el is None:
                        return {"error": f"Element not found: {selector}"}
                    raw = await el.screenshot(**opts)
                else:
                    raw = await page.screenshot(**opts)

                b64 = base64.b64encode(raw).decode() if not path else None
                return {
                    "success": True,
                    "path": path,
                    "format": format,
                    "size_bytes": len(raw),
                    "base64": (b64[:1000] + "...")
                    if b64 and len(b64) > 1000
                    else b64,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def generate_pdf(
            path: Optional[str] = None,
            format: str = "A4",
            landscape: bool = False,
            print_background: bool = True,
            margin_top: str = "1cm",
            margin_bottom: str = "1cm",
            margin_left: str = "1cm",
            margin_right: str = "1cm",
        ) -> Dict[str, Any]:
            """Generate a PDF from the current page (Chromium only)."""
            try:
                page = await self._active_page()
                opts: Dict[str, Any] = {
                    "format": format,
                    "landscape": landscape,
                    "print_background": print_background,
                    "margin": {
                        "top": margin_top,
                        "bottom": margin_bottom,
                        "left": margin_left,
                        "right": margin_right,
                    },
                }
                if path:
                    opts["path"] = path
                raw = await page.pdf(**opts)
                return {
                    "success": True,
                    "path": path,
                    "size_bytes": len(raw),
                    "base64": base64.b64encode(raw).decode()[:500] + "...",
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def wait_for_selector(
            selector: str,
            state: str = "visible",
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Wait until an element reaches the given state.

            Args:
                selector: CSS selector
                state: visible | hidden | attached | detached
                timeout: Milliseconds before timeout
            """
            try:
                page = await self._active_page()
                await page.wait_for_selector(
                    selector, state=state, timeout=timeout or self.timeout
                )
                return {"success": True, "selector": selector, "state": state}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def wait_for_load(
            timeout: Optional[int] = None,
            wait_until: str = "load",
        ) -> Dict[str, Any]:
            """Wait for the page to finish loading."""
            try:
                page = await self._active_page()
                await page.wait_for_load_state(
                    wait_until, timeout=timeout or self.timeout
                )
                return {"success": True, "url": page.url, "title": await page.title()}
            except Exception as e:
                return {"error": str(e)}

    # ---- Network tools -----------------------------------------------

    def _register_network_tools(self):

        @self.mcp_server.tool()
        async def get_cookies(urls: Optional[List[str]] = None) -> Dict[str, Any]:
            """Get browser cookies."""
            try:
                inst = await self._get_or_create_session()
                cookies = await inst["context"].cookies(urls)
                return {"success": True, "count": len(cookies), "cookies": cookies}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def set_cookies(cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
            """Set browser cookies."""
            try:
                inst = await self._get_or_create_session()
                await inst["context"].add_cookies(cookies)
                return {"success": True, "count": len(cookies)}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def clear_cookies() -> Dict[str, Any]:
            """Clear all browser cookies."""
            try:
                inst = await self._get_or_create_session()
                await inst["context"].clear_cookies()
                return {"success": True, "message": "All cookies cleared"}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def get_local_storage() -> Dict[str, Any]:
            """Get all localStorage key/value pairs."""
            try:
                page = await self._active_page()
                data = await page.evaluate(
                    """() => {
                        const d = {};
                        for (let i = 0; i < localStorage.length; i++) {
                            const k = localStorage.key(i);
                            d[k] = localStorage.getItem(k);
                        }
                        return d;
                    }"""
                )
                return {"success": True, "count": len(data), "data": data}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def set_local_storage(data: Dict[str, str]) -> Dict[str, Any]:
            """Set localStorage key/value pairs."""
            try:
                page = await self._active_page()
                await page.evaluate(
                    """(d) => {
                        Object.entries(d).forEach(([k, v]) => localStorage.setItem(k, v));
                    }""",
                    data,
                )
                return {"success": True, "count": len(data)}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def intercept_requests(
            url_pattern: str, action: str = "block"
        ) -> Dict[str, Any]:
            """Intercept matching network requests.

            Args:
                url_pattern: URL glob pattern
                action: block | continue
            """
            try:
                page = await self._active_page()

                async def handle(route):
                    if action == "block":
                        await route.abort()
                    else:
                        await route.continue_()

                await page.route(url_pattern, handle)
                return {"success": True, "pattern": url_pattern, "action": action}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def mock_api_response(
            url_pattern: str,
            response_body: Any,
            status: int = 200,
            headers: Optional[Dict[str, str]] = None,
        ) -> Dict[str, Any]:
            """Mock responses for requests matching url_pattern."""
            try:
                page = await self._active_page()
                body = (
                    json.dumps(response_body)
                    if isinstance(response_body, (dict, list))
                    else str(response_body)
                )

                async def handle(route):
                    await route.fulfill(
                        status=status,
                        headers=headers or {"Content-Type": "application/json"},
                        body=body,
                    )

                await page.route(url_pattern, handle)
                return {"success": True, "pattern": url_pattern, "status": status}
            except Exception as e:
                return {"error": str(e)}

    # ---- Advanced tools ----------------------------------------------

    def _register_advanced_tools(self):

        @self.mcp_server.tool()
        async def handle_dialog(
            accept: bool = True,
            prompt_text: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Register a one-shot handler for the next JS dialog."""
            try:
                page = await self._active_page()

                async def on_dialog(dialog):
                    if prompt_text and dialog.type == "prompt":
                        await dialog.accept(prompt_text)
                    elif accept:
                        await dialog.accept()
                    else:
                        await dialog.dismiss()

                page.once("dialog", on_dialog)
                return {"success": True, "message": "Dialog handler registered"}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def emulate_device(device_name: str) -> Dict[str, Any]:
            """Emulate a mobile/tablet device by name (e.g. 'iPhone 13')."""
            try:
                pw = await self._ensure_playwright()
                device = pw.devices.get(device_name)
                if device is None:
                    available = list(pw.devices.keys())[:15]
                    return {
                        "error": f"Device '{device_name}' not found",
                        "sample_devices": available,
                    }

                inst = await self._get_or_create_session()
                new_ctx = await inst["browser"].new_context(**device)
                new_page = await new_ctx.new_page()
                await inst["context"].close()
                inst["context"] = new_ctx
                inst["page"] = new_page

                return {
                    "success": True,
                    "device": device_name,
                    "viewport": device.get("viewport"),
                    "user_agent": device.get("user_agent"),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def set_geolocation(
            latitude: float,
            longitude: float,
            accuracy: Optional[float] = None,
        ) -> Dict[str, Any]:
            """Override geolocation for the active context."""
            try:
                inst = await self._get_or_create_session()
                geo: Dict[str, Any] = {
                    "latitude": latitude,
                    "longitude": longitude,
                }
                if accuracy is not None:
                    geo["accuracy"] = accuracy
                await inst["context"].set_geolocation(geo)
                return {
                    "success": True,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def set_viewport_size(width: int, height: int) -> Dict[str, Any]:
            """Resize the viewport."""
            try:
                page = await self._active_page()
                await page.set_viewport_size({"width": width, "height": height})
                return {"success": True, "width": width, "height": height}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def drag_and_drop(
            source_selector: str,
            target_selector: str,
            steps: int = 10,
        ) -> Dict[str, Any]:
            """Drag an element and drop it onto another."""
            try:
                page = await self._active_page()
                source = await page.query_selector(source_selector)
                target = await page.query_selector(target_selector)
                if not source:
                    return {"error": f"Source not found: {source_selector}"}
                if not target:
                    return {"error": f"Target not found: {target_selector}"}
                # Note: async Playwright doesn't have drag_to with steps
                # on ElementHandle; use page.drag_and_drop instead
                await page.drag_and_drop(source_selector, target_selector)
                return {
                    "success": True,
                    "source": source_selector,
                    "target": target_selector,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def new_tab(url: Optional[str] = None) -> Dict[str, Any]:
            """Open a new browser tab."""
            try:
                inst = await self._get_or_create_session()
                tab = await inst["context"].new_page()
                if url:
                    await tab.goto(url)
                return {
                    "success": True,
                    "tab_count": len(inst["context"].pages),
                    "url": tab.url,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def switch_tab(index: int) -> Dict[str, Any]:
            """Switch active tab by index."""
            try:
                inst = await self._get_or_create_session()
                pages = inst["context"].pages
                if index < 0 or index >= len(pages):
                    return {
                        "error": f"Index {index} out of range (0-{len(pages)-1})"
                    }
                inst["page"] = pages[index]
                return {"success": True, "index": index, "url": pages[index].url}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def close_tab(index: Optional[int] = None) -> Dict[str, Any]:
            """Close a tab by index (defaults to last tab)."""
            try:
                inst = await self._get_or_create_session()
                pages = inst["context"].pages
                if len(pages) == 1:
                    return {"error": "Cannot close the last tab"}
                idx = index if index is not None else len(pages) - 1
                if idx < 0 or idx >= len(pages):
                    return {"error": f"Index {idx} out of range"}
                target_page = pages[idx]
                if inst["page"] == target_page:
                    inst["page"] = pages[0] if idx != 0 else pages[1]
                await target_page.close()
                return {
                    "success": True,
                    "remaining_tabs": len(inst["context"].pages),
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def download_file(
            trigger_selector: str,
            timeout: Optional[int] = None,
        ) -> Dict[str, Any]:
            """Click a download link and wait for the file to arrive."""
            try:
                page = await self._active_page()
                async with page.expect_download(
                    timeout=(timeout or self.timeout) * 2
                ) as dl_info:
                    await page.click(trigger_selector)
                dl = dl_info.value
                save_path = os.path.join(
                    self.downloads_path, dl.suggested_filename
                )
                await dl.save_as(save_path)
                return {
                    "success": True,
                    "filename": dl.suggested_filename,
                    "save_path": save_path,
                    "url": dl.url,
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def listen_console() -> Dict[str, Any]:
            """Start capturing browser console messages."""
            try:
                inst = await self._get_or_create_session()
                messages: List[Dict[str, Any]] = []
                inst["console_messages"] = messages

                def on_msg(msg):
                    messages.append(
                        {
                            "type": msg.type,
                            "text": msg.text,
                            "location": msg.location,
                        }
                    )

                inst["page"].on("console", on_msg)
                return {"success": True, "message": "Console listener started"}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def get_console_logs() -> Dict[str, Any]:
            """Return captured console messages."""
            try:
                inst = await self._get_or_create_session()
                logs = inst.get("console_messages", [])
                return {"success": True, "count": len(logs), "logs": logs}
            except Exception as e:
                return {"error": str(e)}


# ---------------------------------------------------------------------------
# CLI entry point lives in mcp_arena.cli (Typer-based).
# ---------------------------------------------------------------------------
