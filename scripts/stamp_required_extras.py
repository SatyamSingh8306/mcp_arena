"""Stamp every preset with a `_REQUIRED_EXTRAS` dict.

Idempotent: replaces any existing _REQUIRED_EXTRAS line. Run from the repo root.
"""
from pathlib import Path

PRESETS = Path("mcp_arena/presents")

# module_name -> {import_name: extra_name}
MAP = {
    "audio":          {"pydub": "audio", "librosa": "audio", "numpy": "audio"},
    "aws":            {"boto3": "cloudstorage"},
    "bitbucket":      {"atlassian": "bitbucket"},
    "browser":        {"playwright": "browser", "cv2": "browser", "PIL": "browser"},
    "cloudstorage":   {"boto3": "cloudstorage", "google.cloud.storage": "cloudstorage"},
    "confluence":     {"atlassian": "bitbucket", "html2text": "bitbucket"},
    "docker":         {"docker": "docker"},
    "generic_api":    {"httpx": "generic_api"},
    "github":         {"github": "github"},
    "gitlab":         {"gitlab": "gitlab"},
    "image":          {"PIL": "image", "cv2": "image"},
    "jira":           {"atlassian": "bitbucket"},
    # local_operation / smtp / generic_api are moving into core; still stamp
    # the dict so the constructor pattern is consistent across all presets.
    "local_operation": {"psutil": "local_operation", "pyautogui": "local_operation"},
    "mail":           {"googleapiclient": "mail", "msal": "mail"},
    "mongo":          {"pymongo": "mongodb", "bson": "mongodb"},
    "notification":   {"slack_sdk": "notification", "requests": "notification"},
    "notion":         {"notion_client": "notion"},
    "outlook":        {"msal": "outlook", "requests": "outlook"},
    "pdf":            {"fitz": "pdf", "PyPDF2": "pdf", "reportlab": "pdf", "pdfplumber": "pdf"},
    "postgres":       {"psycopg2": "postgres"},
    "qrcode":         {"qrcode": "qrcode", "PIL": "qrcode"},
    "redis":          {"redis": "redis"},
    "screencapture":  {"pyautogui": "screencapture"},
    "slack":          {"slack_sdk": "slack"},
    "smtp":           {},  # pure stdlib — core
    "spreadsheet":    {"pandas": "spreadsheet", "openpyxl": "spreadsheet"},
    "vectordb":       {
        "chromadb": "vectordb",
        "langchain_huggingface": "vectordb",
        "langchain_openai": "vectordb",
        "langchain_chroma": "vectordb",
        "langchain_community": "vectordb",
    },
    "video":          {"moviepy": "video", "numpy": "video"},
    "webscraping":    {"requests": "webscraping", "bs4": "webscraping", "selenium": "webscraping"},
    "whatsapp":       {"twilio": "whatsapp"},
}


def stamp(path: Path, extras: dict) -> None:
    """Insert `_REQUIRED_EXTRAS = {...}` as the FIRST statement inside the class body.

    Targets `class FooMCPServer(BaseMCPServer):` and inserts on the next non-blank,
    non-docstring line so it lands at the top of the class body.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    # Drop any leftover stamp from a prior run.
    out = [l for l in lines if not l.lstrip().startswith("_REQUIRED_EXTRAS = ")]

    if extras:
        body = ", ".join(f'"{k}": "{v}"' for k, v in sorted(extras.items()))
        new_line = f"    _REQUIRED_EXTRAS = {{{body}}}\n"
    else:
        new_line = "    _REQUIRED_EXTRAS = {}\n"

    inserted = False
    for i, line in enumerate(out):
        # Find the MCP-server class — must inherit from BaseMCPServer (not the base itself).
        if line.startswith("class ") and "(BaseMCPServer)" in line and "BaseMCPServer(ABC)" not in line:
            insert_at = i + 1
            # Skip the class docstring if present.
            j = insert_at
            # Skip leading blank lines.
            while j < len(out) and out[j].strip() == "":
                j += 1
            # If the next non-blank line opens a docstring, find its close.
            if j < len(out):
                stripped = out[j].lstrip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    quote = stripped[:3]
                    # Single-line docstring?
                    if stripped.count(quote) >= 2 and len(stripped) > 3:
                        insert_at = j + 1
                    else:
                        # Multi-line: advance past the closing triple-quote.
                        k = j + 1
                        while k < len(out):
                            if quote in out[k]:
                                insert_at = k + 1
                                break
                            k += 1
                        else:
                            insert_at = j + 1
                else:
                    insert_at = j
            out.insert(insert_at, new_line)
            inserted = True
            break
    if not inserted:
        out.append("\n" + new_line)
    path.write_text("".join(out), encoding="utf-8")
    print(f"  stamped {path.name}: {len(extras)} dep(s)")


def main() -> None:
    for module, extras in sorted(MAP.items()):
        path = PRESETS / f"{module}.py"
        if not path.exists():
            print(f"  SKIP (no file): {path}")
            continue
        stamp(path, extras)


if __name__ == "__main__":
    main()
