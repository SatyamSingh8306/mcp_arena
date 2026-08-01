"""Web scraping MCP server: requests + BeautifulSoup, with email/phone extraction."""
import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    import requests as _requests_lib
except ImportError:
    _requests_lib = None

try:
    from bs4 import BeautifulSoup as _BeautifulSoup
except ImportError:
    _BeautifulSoup = None


def _ensure_requests():
    if _requests_lib is None:
        raise ImportError("requests is required. pip install requests")
    return _requests_lib


def _ensure_bs4():
    if _BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required. pip install beautifulsoup4")
    return _BeautifulSoup


class WebScrapingMCPServer(BaseMCPServer):
    """Web scraping MCP server."""
    _REQUIRED_EXTRAS = {"bs4": "webscraping", "requests": "webscraping", "selenium": "webscraping"}

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        user_agent: str = "MCP-WebScraper/1.0",
        timeout: int = 30,
        delay: float = 1.0,
        proxies: Optional[Dict[str, str]] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "scraping_output")
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay = delay
        self.proxies = proxies
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)
        self._session = None

        super().__init__(
            name="Web Scraping MCP Server",
            description="MCP server for web scraping and data extraction",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _session_obj(self):
        if self._session is None:
            requests = _ensure_requests()
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": self.user_agent})
            if self.proxies:
                self._session.proxies.update(self.proxies)
        return self._session

    def _register_tools(self) -> None:
        self._register_basic_tools()
        self._register_extraction_tools()
        self._register_api_tools()

    def _register_basic_tools(self):
        @self.mcp_server.tool()
        def scrape_website(
            url: str,
            output_format: str = "json",
            output_path: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Scrape a URL and return structured content."""
            try:
                start = time.time()
                session = self._session_obj()
                response = session.get(url, timeout=self.timeout)
                response.raise_for_status()
                soup = _ensure_bs4()(response.text, "html.parser")
                result = {
                    "url": url,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "title": soup.title.text if soup.title else None,
                    "text": soup.get_text(),
                    "html": response.text,
                    "links": [a.get("href") for a in soup.find_all("a") if a.get("href")],
                    "images": [img.get("src") for img in soup.find_all("img") if img.get("src")],
                }
                if output_path is None:
                    base_name = re.sub(r"[^a-zA-Z0-9]", "_", url)
                    output_path = os.path.join(self.default_output_dir, f"{base_name}.{output_format}")
                self._save_data(result, output_path, output_format)
                return {
                    "success": True,
                    "url": url,
                    "output_path": output_path,
                    "execution_time": round(time.time() - start, 2),
                    "data_size": len(str(result)),
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def get_website_info(url: str) -> Dict[str, Any]:
            """Get website metadata (title, description, status code, headers)."""
            try:
                start = time.time()
                response = self._session_obj().get(url, timeout=self.timeout)
                soup = _ensure_bs4()(response.text, "html.parser")
                title_tag = soup.find("title")
                desc_tag = soup.find("meta", attrs={"name": "description"})
                html_tag = soup.find("html")
                return {
                    "success": True,
                    "info": {
                        "url": url,
                        "title": title_tag.text.strip() if title_tag else "No title",
                        "description": desc_tag.get("content") if desc_tag else None,
                        "language": html_tag.get("lang") if html_tag else None,
                        "charset": response.encoding,
                        "response_time": round(time.time() - start, 2),
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "content_type": response.headers.get("content-type", ""),
                        "content_length": int(response.headers.get("content-length", 0)),
                    },
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def scrape_multiple_pages(
            urls: List[str],
            output_dir: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Scrape multiple URLs sequentially."""
            output_dir = output_dir or self.default_output_dir
            results = []
            for url in urls:
                results.append(scrape_website(url, "json", None))
                time.sleep(self.delay)
            return {"success": True, "urls_count": len(urls), "results": results, "output_dir": output_dir}

        @self.mcp_server.tool()
        def scrape_with_pagination(
            base_url: str,
            page_param: str = "page",
            start_page: int = 1,
            end_page: int = 10,
            output_dir: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Scrape pages with `?page=N` style pagination."""
            output_dir = output_dir or os.path.join(self.default_output_dir, "paginated")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            results = []
            for page in range(start_page, end_page + 1):
                url = f"{base_url}?{page_param}={page}"
                results.append(scrape_website(url, "json", None))
                time.sleep(self.delay)
            return {
                "success": True,
                "pages_scraped": end_page - start_page + 1,
                "results": results,
                "output_dir": output_dir,
            }

    def _register_extraction_tools(self):
        @self.mcp_server.tool()
        def extract_structured_data(
            url: str,
            selectors: Dict[str, str],
            output_format: str = "json",
            output_path: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Extract data from a URL using CSS selectors."""
            try:
                response = self._session_obj().get(url, timeout=self.timeout)
                response.raise_for_status()
                soup = _ensure_bs4()(response.text, "html.parser")
                extracted = {}
                for key, selector in selectors.items():
                    elements = soup.select(selector)
                    if not elements:
                        extracted[key] = None
                    elif len(elements) == 1:
                        extracted[key] = elements[0].get_text().strip()
                    else:
                        extracted[key] = [elem.get_text().strip() for elem in elements]
                if output_path is None:
                    base_name = re.sub(r"[^a-zA-Z0-9]", "_", url)
                    output_path = os.path.join(self.default_output_dir, f"{base_name}_structured.{output_format}")
                self._save_data(extracted, output_path, output_format)
                return {
                    "success": True,
                    "url": url,
                    "data_extracted": len(extracted),
                    "output_path": output_path,
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def extract_emails(url: str) -> Dict[str, Any]:
            """Extract email addresses from a webpage."""
            try:
                response = self._session_obj().get(url, timeout=self.timeout)
                response.raise_for_status()
                pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                emails = list(set(re.findall(pattern, response.text)))
                return {
                    "success": True,
                    "url": url,
                    "emails_found": len(emails),
                    "emails": emails,
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def extract_phone_numbers(url: str) -> Dict[str, Any]:
            """Extract phone numbers from a webpage."""
            try:
                response = self._session_obj().get(url, timeout=self.timeout)
                response.raise_for_status()
                pattern = r"\b(?:\(\d{3}\)\s?|\d{3}[-.]?)?\d{3}[-.]?\d{4}\b"
                phones = list(set(re.findall(pattern, response.text)))
                return {
                    "success": True,
                    "url": url,
                    "phones_found": len(phones),
                    "phone_numbers": phones,
                }
            except Exception as exc:
                return {"error": str(exc)}

    def _register_api_tools(self):
        @self.mcp_server.tool()
        def make_api_request(
            url: str,
            method: str = "GET",
            headers: Optional[Dict[str, str]] = None,
            data: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """Make an HTTP request and return the response."""
            try:
                kwargs = {"headers": headers or {}, "timeout": self.timeout}
                if data:
                    kwargs["json"] = data
                response = self._session_obj().request(method.upper(), url, **kwargs)
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text[:5000] if len(response.text) > 5000 else response.text,
                }
            except Exception as exc:
                return {"error": str(exc)}

    def _save_data(self, data: Any, output_path: str, format: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            if format == "json":
                json.dump(data, f, indent=2, ensure_ascii=False)
            elif format == "csv":
                if isinstance(data, list):
                    writer = csv.DictWriter(f, fieldnames=data[0].keys() if data else [])
                    writer.writeheader()
                    writer.writerows(data)
                else:
                    writer = csv.writer(f)
                    for key, value in data.items():
                        writer.writerow([key, value])
            elif format == "html":
                f.write(data.get("html", "") if isinstance(data, dict) else str(data))
            else:
                f.write(str(data))

