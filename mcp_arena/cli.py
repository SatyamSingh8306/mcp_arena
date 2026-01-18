"""
CLI for mcp_arena using Typer
"""

import sys
import os
import importlib
import inspect
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Type, Tuple
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.tree import Tree

app = typer.Typer(
    name="mcp-arena",
    help="CLI for running MCP servers from mcp_arena presets.",
    add_completion=True,
)
console = Console()

PRESETS_DIR = Path(__file__).parent / "presents"

# Company Information
COMPANY_INFO = {
    "name": "MCP Arena",
    "description": "Production-ready Python library for building MCP (Model Context Protocol) servers with intelligent agent orchestration.",
    "website": "https://mcparena.vercel.app/",
    "github": "https://github.com/SatyamSingh8306/mcp_arena",
    "pypi": "https://pypi.org/project/mcp-arena/",
    "documentation": "https://mcparena.vercel.app/docs",
    "community": "https://github.com/SatyamSingh8306/mcp_arena/discussions",
    "issues": "https://github.com/SatyamSingh8306/mcp_arena/issues",
    "version": "0.2.3",
    "license": "MIT",
    "author": "Satyam Singh",
    "tagline": "Build. Deploy. Orchestrate."
}

# Color scheme
COLORS = {
    "primary": "bright_blue",
    "success": "bright_green",
    "error": "bright_red",
    "warning": "bright_yellow",
    "info": "bright_cyan",
    "muted": "dim white",
    "accent": "bright_magenta",
}


class AnimatedProgress:
    """Handles animated progress displays."""
    
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    @staticmethod
    def create_progress_bar() -> Progress:
        """Create a styled progress bar."""
        return Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style=COLORS["success"], finished_style=COLORS["success"]),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        )


def create_company_footer() -> Panel:
    """Create a footer panel with company information and links."""
    footer_content = Text()
    footer_content.append("\n", style="")
    footer_content.append("[+] ", style="bold bright_yellow")
    footer_content.append(f"{COMPANY_INFO['name']} - {COMPANY_INFO['tagline']}", style=f"bold {COLORS['primary']}")
    footer_content.append("\n\n", style="")
    
    links = [
        ("[DOC] Documentation", COMPANY_INFO["documentation"]),
        ("[WEB] Website", COMPANY_INFO["website"]),
        ("[GIT] GitHub", COMPANY_INFO["github"]),
        ("[PYPI] PyPI", COMPANY_INFO["pypi"]),
        ("[COM] Community", COMPANY_INFO["community"]),
        ("[ISS] Issues", COMPANY_INFO["issues"])
    ]
    
    for emoji, link in links:
        footer_content.append(f"{emoji} ", style="")
        footer_content.append(link, style=f"link {COLORS['info']}")
        footer_content.append("\n", style="")
    
    return Panel(
        footer_content,
        title=f"[bold]{COMPANY_INFO['name']} v{COMPANY_INFO['version']}[/bold]",
        box=box.ROUNDED,
        style=COLORS["muted"],
        padding=(1, 2)
    )


def create_header(title: str, subtitle: str = "") -> Panel:
    """Create a stylized header panel."""
    header_content = Text()
    header_content.append(title, style=f"bold {COLORS['primary']}")
    if subtitle:
        header_content.append(f"\n{subtitle}", style=COLORS["muted"])
    
    return Panel(
        Align.center(header_content),
        box=box.DOUBLE,
        style=COLORS["primary"],
        padding=(0, 2),
    )


def create_status_panel(
    title: str,
    message: str,
    status: str = "info",
    details: Optional[Dict[str, str]] = None
) -> Panel:
    """Create a status panel with optional details."""
    status_colors = {
        "info": COLORS["info"],
        "success": COLORS["success"],
        "error": COLORS["error"],
        "warning": COLORS["warning"],
    }
    
    content = f"[bold {status_colors.get(status, COLORS['info'])}]{message}[/bold {status_colors.get(status, COLORS['info'])}]"
    
    if details:
        content += "\n\n"
        for key, value in details.items():
            content += f"[{COLORS['primary']}]{key}:[/{COLORS['primary']}] [{COLORS['muted']}]{value}[/{COLORS['muted']}]\n"
    
    return Panel(
        content,
        title=f"[bold]{title}[/bold]",
        box=box.ROUNDED,
        style=status_colors.get(status, COLORS["info"]),
        padding=(1, 2),
    )


def _get_available_presets() -> Dict[str, str]:
    """
    Scans the 'presents' directory to find available server modules.
    Returns a dict of {server_name: module_name}.
    """
    presets = {}
    if not PRESETS_DIR.exists():
        return presets

    seen_files = set()
    for file in PRESETS_DIR.glob("*.py"):
        if file.name.startswith("__") or file.name.startswith("base"):
            continue
        
        if file.name in seen_files:
            continue
        seen_files.add(file.name)
        
        module_name = file.stem
        presets[module_name] = module_name
    
    return presets


def _load_server_class(module_name: str) -> Optional[Type]:
    """
    Dynamically imports the module and finds the MCPServer class.
    """
    try:
        module = importlib.import_module(f"mcp_arena.presents.{module_name}")
        from mcp_arena.mcp.server import BaseMCPServer
        
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj) 
                and issubclass(obj, BaseMCPServer) 
                and obj is not BaseMCPServer
            ):
                return obj
        
        return None
        
    except ImportError as e:
        console.print(f"[{COLORS['error']}]Failed to import module {module_name}: {e}[/{COLORS['error']}]")
        return None
    except Exception as e:
        console.print(f"[{COLORS['error']}]Error loading class from {module_name}: {e}[/{COLORS['error']}]")
        return None


def _parse_server_params(server_class: Type) -> List[Tuple[str, bool, Any]]:
    """
    Parse server class __init__ parameters.
    Returns list of (param_name, is_required, default_value).
    """
    params = []
    try:
        sig = inspect.signature(server_class.__init__)
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            is_required = param.default == inspect.Parameter.empty
            default = None if is_required else param.default
            params.append((name, is_required, default))
    except Exception:
        pass
    
    return params


@app.command("about")
def show_about():
    """
    Display information about MCP Arena and company details.
    """
    console.print(create_header("ABOUT MCP ARENA", COMPANY_INFO["tagline"]))
    console.print()
    
    # Company overview
    overview_content = Text()
    overview_content.append(COMPANY_INFO["description"], style=COLORS["muted"])
    overview_content.append("\n\n", style="")
    overview_content.append("Version: ", style=f"bold {COLORS['primary']}")
    overview_content.append(COMPANY_INFO["version"], style=COLORS["success"])
    overview_content.append(" | ", style=COLORS["muted"])
    overview_content.append("License: ", style=f"bold {COLORS['primary']}")
    overview_content.append(COMPANY_INFO["license"], style=COLORS["success"])
    overview_content.append(" | ", style=COLORS["muted"])
    overview_content.append("Author: ", style=f"bold {COLORS['primary']}")
    overview_content.append(COMPANY_INFO["author"], style=COLORS["success"])
    
    console.print(Panel(
        overview_content,
        title="[bold]Project Overview[/bold]",
        box=box.ROUNDED,
        style=COLORS["info"],
        padding=(1, 2)
    ))
    console.print()
    
    # Key features
    features = [
        "[+] 17+ Production-ready MCP server presets",
        "[+] 4 Intelligent agent types (Reflection, ReAct, Planning, Router)",
        "[+] Zero-configuration setup for common use cases",
        "[+] Extensible SOLID architecture",
        "[+] Modular design - use only what you need",
        "[+] Seamless LangChain integration",
        "[+] Comprehensive documentation"
    ]
    
    features_content = "\n".join([f"* {feature}" for feature in features])
    
    console.print(Panel(
        features_content,
        title="[bold]Key Features[/bold]",
        box=box.ROUNDED,
        style=COLORS["primary"],
        padding=(1, 2)
    ))
    console.print()
    
    # Quick links table
    links_table = Table(
        title="Quick Links",
        box=box.ROUNDED,
        show_header=True,
        header_style=f"bold {COLORS['primary']}",
        border_style=COLORS["primary"]
    )
    links_table.add_column("Resource", style=COLORS["info"], width=15)
    links_table.add_column("Link", style=f"link {COLORS['info']}")
    
    links = [
        ("[DOC] Documentation", COMPANY_INFO["documentation"]),
        ("[WEB] Website", COMPANY_INFO["website"]),
        ("[GIT] GitHub Repository", COMPANY_INFO["github"]),
        ("[PYPI] PyPI Package", COMPANY_INFO["pypi"]),
        ("[COM] Community Forum", COMPANY_INFO["community"]),
        ("[ISS] Report Issues", COMPANY_INFO["issues"])
    ]
    
    for resource, link in links:
        links_table.add_row(resource, link)
    
    console.print(links_table)
    console.print()
    
    # Call to action
    cta_content = Text()
    cta_content.append("[*] ", style="bold bright_yellow")
    cta_content.append("Star us on GitHub to support the project!", style=f"bold {COLORS['primary']}")
    cta_content.append("\n[!] ", style="bold bright_yellow")
    cta_content.append("Join our community for updates and discussions.", style=COLORS["muted"])
    cta_content.append("\n[+] ", style="bold bright_yellow")
    cta_content.append("Try 'mcp-arena list' to see available presets!", style=COLORS["success"])
    
    console.print(Panel(
        cta_content,
        title="[bold]Get Started[/bold]",
        box=box.DOUBLE,
        style=COLORS["accent"],
        padding=(1, 2)
    ))
    
    console.print()
    console.print(create_company_footer())


@app.command("list")
def list_presets(
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information for each preset")
):
    """
    List all available MCP server presets.
    """
    console.print(create_header("MCP ARENA", "Available Server Presets"))
    console.print()
    
    presets = _get_available_presets()
    
    if not presets:
        console.print(Panel(
            f"[{COLORS['warning']}]No presets found in the presents directory.[/{COLORS['warning']}]",
            title="No Presets",
            box=box.ROUNDED,
            style=COLORS["warning"]
        ))
        return
    
    if detailed:
        for name in sorted(presets.keys()):
            server_class = _load_server_class(presets[name])
            if server_class:
                params = _parse_server_params(server_class)
                
                details = {
                    "Module": f"mcp_arena.presents.{name}",
                    "Class": server_class.__name__,
                    "Parameters": f"{len(params)} parameter(s)" if params else "No parameters"
                }
                
                console.print(Panel(
                    "\n".join([f"[{COLORS['primary']}]{k}:[/{COLORS['primary']}] [{COLORS['muted']}]{v}[/{COLORS['muted']}]" 
                              for k, v in details.items()]),
                    title=f"[bold {COLORS['success']}]{name}[/bold {COLORS['success']}]",
                    box=box.ROUNDED,
                    padding=(1, 2)
                ))
            console.print()
    else:
        table = Table(
            title=f"Found {len(presets)} Preset(s)",
            box=box.ROUNDED,
            show_header=True,
            header_style=f"bold {COLORS['primary']}",
            border_style=COLORS["primary"]
        )
        table.add_column("Preset Name", style=COLORS["success"], no_wrap=True, width=20)
        table.add_column("Module Path", style=COLORS["muted"])
        table.add_column("Status", style=COLORS["info"], justify="center", width=12)
        
        for name in sorted(presets.keys()):
            server_class = _load_server_class(presets[name])
            status = "[OK] Ready" if server_class else "[ERR] Error"
            table.add_row(name, f"mcp_arena.presents.{name}", status)
        
        console.print(table)
        console.print()
        console.print(f"[{COLORS['muted']}]Tip: Use [bold]--detailed[/bold] flag for more information[/{COLORS['muted']}]")
        console.print()
        console.print(create_company_footer())


@app.command("info")
def show_preset_info(
    preset_name: str = typer.Argument(..., help="Name of the preset to inspect")
):
    """
    Show detailed information about a specific MCP server preset.
    """
    console.print(create_header("PRESET INFORMATION", f"Inspecting: {preset_name}"))
    console.print()
    
    presets = _get_available_presets()
    if preset_name not in presets:
        console.print(create_status_panel(
            "Error",
            f"Server preset '{preset_name}' not found.",
            "error",
            {"Suggestion": "Run 'mcp-arena list' to see available presets"}
        ))
        raise typer.Exit(code=1)
    
    server_class = _load_server_class(presets[preset_name])
    if not server_class:
        console.print(create_status_panel(
            "Error",
            f"Could not load MCPServer class from preset '{preset_name}'.",
            "error"
        ))
        raise typer.Exit(code=1)
    
    # Create info tree
    tree = Tree(f"[bold {COLORS['success']}]{preset_name}[/bold {COLORS['success']}]")
    
    # Basic info
    basic_branch = tree.add(f"[{COLORS['primary']}]Basic Information[/{COLORS['primary']}]")
    basic_branch.add(f"Class Name: [{COLORS['muted']}]{server_class.__name__}[/{COLORS['muted']}]")
    basic_branch.add(f"Module: [{COLORS['muted']}]mcp_arena.presents.{preset_name}[/{COLORS['muted']}]")
    
    # Description
    if server_class.__doc__:
        desc = server_class.__doc__.strip().split('\n')[0][:100]
        basic_branch.add(f"Description: [{COLORS['muted']}]{desc}[/{COLORS['muted']}]")
    
    # Parameters
    params = _parse_server_params(server_class)
    if params:
        param_branch = tree.add(f"[{COLORS['primary']}]Parameters ({len(params)})[/{COLORS['primary']}]")
        for param_name, is_required, default in params:
            if is_required:
                param_branch.add(f"[{COLORS['error']}]--{param_name}[/{COLORS['error']}] (required)")
            else:
                param_branch.add(f"[{COLORS['info']}]--{param_name}[/{COLORS['info']}] (default: {default})")
    else:
        tree.add(f"[{COLORS['muted']}]No parameters required[/{COLORS['muted']}]")
    
    console.print(Panel(
        tree,
        title="[bold]Server Details[/bold]",
        box=box.ROUNDED,
        padding=(1, 2)
    ))
    console.print()
    console.print(f"[{COLORS['muted']}]Usage: [bold]mcp-arena run --mcp-server {preset_name} [OPTIONS][/bold][/{COLORS['muted']}]")
    console.print()
    console.print(create_company_footer())


def _parse_cli_args(args: List[str]) -> Dict[str, Any]:
    """Parse command line arguments into a dictionary."""
    kwargs = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg.lstrip("-").replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                value = args[i + 1]
                # Try to convert to appropriate type
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                kwargs[key] = value
                i += 2
            else:
                kwargs[key] = True
                i += 1
        else:
            i += 1
    return kwargs


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def run(
    ctx: typer.Context,
    mcp_server: str = typer.Option(
        ..., 
        "--mcp-server", 
        "-s", 
        help="Name of the MCP server preset to run"
    ),
    verbose: bool = typer.Option(
        False, 
        "--verbose", 
        "-v", 
        help="Enable verbose output"
    ),
):
    """
    Run an MCP server preset with enhanced UI and progress tracking.
    
    Additional server-specific arguments can be passed as --argument-name value.
    """
    stages = [
        ("Validating preset", 0.2),
        ("Loading module", 0.4),
        ("Parsing configuration", 0.2),
        ("Initializing server", 0.2),
    ]
    
    with Progress(*AnimatedProgress.create_progress_bar().columns, console=console) as progress:
        task = progress.add_task("[cyan]Starting MCP Server...", total=100)
        
        # Stage 1: Validation
        progress.update(task, description=f"[{COLORS['info']}]{stages[0][0]}...")
        presets = _get_available_presets()
        
        if mcp_server not in presets:
            progress.stop()
            console.print()
            console.print(create_status_panel(
                "Error",
                f"Server preset '{mcp_server}' not found.",
                "error",
                {
                    "Available Presets": f"{len(presets)} found",
                    "Suggestion": "Run 'mcp-arena list' to see all presets"
                }
            ))
            raise typer.Exit(code=1)
        
        progress.advance(task, stages[0][1] * 100)
        time.sleep(0.3)
        
        # Stage 2: Loading
        progress.update(task, description=f"[{COLORS['info']}]{stages[1][0]}...")
        server_class = _load_server_class(presets[mcp_server])
        
        if not server_class:
            progress.stop()
            console.print()
            console.print(create_status_panel(
                "Error",
                "Failed to load server class.",
                "error",
                {"Module": f"mcp_arena.presents.{mcp_server}"}
            ))
            raise typer.Exit(code=1)
        
        progress.advance(task, stages[1][1] * 100)
        time.sleep(0.3)
        
        # Stage 3: Configuration
        progress.update(task, description=f"[{COLORS['info']}]{stages[2][0]}...")
        kwargs = _parse_cli_args(ctx.args)
        
        if verbose:
            console.print(f"\n[{COLORS['muted']}]Parsed arguments: {kwargs}[/{COLORS['muted']}]")
        
        progress.advance(task, stages[2][1] * 100)
        time.sleep(0.3)
        
        # Stage 4: Initialization
        progress.update(task, description=f"[{COLORS['info']}]{stages[3][0]}...")
        
        try:
            server_instance = server_class(**kwargs)
            progress.advance(task, stages[3][1] * 100)
            time.sleep(0.3)
            
        except TypeError as e:
            progress.stop()
            console.print()
            params = _parse_server_params(server_class)
            required = [p[0] for p in params if p[1]]
            
            console.print(create_status_panel(
                "Configuration Error",
                str(e),
                "error",
                {
                    "Required Parameters": ", ".join(f"--{p}" for p in required) if required else "None",
                    "Provided Parameters": ", ".join(f"--{k}" for k in kwargs.keys()) if kwargs else "None",
                    "Suggestion": f"Run 'mcp-arena info {mcp_server}' for parameter details"
                }
            ))
            raise typer.Exit(code=1)
        
        except Exception as e:
            progress.stop()
            console.print()
            console.print(create_status_panel(
                "Initialization Error",
                str(e),
                "error"
            ))
            raise typer.Exit(code=1)
        
        progress.update(task, description=f"[{COLORS['success']}]Server initialized successfully!")
        time.sleep(0.5)
    
    console.print()
    
    # Display server information
    details = {
        "Preset": mcp_server,
        "Class": server_class.__name__,
        "Status": "Running",
    }
    
    # Add connection details if available
    if hasattr(server_instance, 'transport'):
        transport = server_instance.transport
        details["Protocol"] = transport.upper()
        
        if transport == "stdio":
            details["Mode"] = "Standard I/O"
            details["Connection"] = "Ready for MCP client"
        elif hasattr(server_instance, 'host') and hasattr(server_instance, 'port'):
            details["Host"] = server_instance.host
            details["Port"] = str(server_instance.port)
            
            if transport == "sse":
                details["Endpoint"] = f"http://{server_instance.host}:{server_instance.port}/sse"
            elif transport == "streamable-http":
                details["Endpoint"] = f"http://{server_instance.host}:{server_instance.port}/mcp"
    
    if kwargs:
        details["Parameters"] = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    
    info_content = "\n".join([
        f"[{COLORS['primary']}]{k}:[/{COLORS['primary']}] [{COLORS['muted']}]{v}[/{COLORS['muted']}]"
        for k, v in details.items()
    ])
    
    console.print(Panel(
        info_content,
        title=f"[bold {COLORS['success']}]Server Active[/bold {COLORS['success']}]",
        box=box.DOUBLE,
        style=COLORS["success"],
        padding=(1, 2)
    ))
    
    console.print()
    console.print(f"[{COLORS['muted']}]Documentation: [link=https://mcparena.vercel.app/]https://mcparena.vercel.app/[/link][/{COLORS['muted']}]")
    console.print()
    
    # Run the server (this will block)
    try:
        server_instance.run()
    except KeyboardInterrupt:
        # Gracefully handle Ctrl+C
        try:
            console.print()
            console.print(f"[{COLORS['warning']}]Server shutdown requested[/{COLORS['warning']}]")
            console.print(f"[{COLORS['muted']}]Goodbye![/{COLORS['muted']}]")
        except (ValueError, BrokenPipeError):
            # Console might be closed, ignore
            pass
    except (ValueError, BrokenPipeError) as e:
        # Handle I/O errors gracefully
        if "closed file" in str(e) or "Broken pipe" in str(e):
            # Server was terminated, this is expected
            pass
        else:
            # Other I/O errors
            try:
                console.print()
                console.print(create_status_panel(
                    "I/O Error",
                    f"Stream closed: {str(e)}",
                    "warning"
                ))
            except (ValueError, BrokenPipeError):
                pass
    except Exception as e:
        try:
            console.print()
            console.print(create_status_panel(
                "Runtime Error",
                str(e),
                "error"
            ))
        except (ValueError, BrokenPipeError):
            # Console might be closed, ignore
            pass
        raise typer.Exit(code=1)


@app.command("validate")
def validate_preset(
    preset_name: str = typer.Argument(..., help="Name of the preset to validate")
):
    """
    Validate a preset's configuration and dependencies.
    """
    console.print(create_header("PRESET VALIDATION", f"Validating: {preset_name}"))
    console.print()
    
    validation_results = []
    
    with Progress(*AnimatedProgress.create_progress_bar().columns, console=console) as progress:
        task = progress.add_task("[cyan]Running validation checks...", total=100)
        
        # Check 1: Preset exists
        progress.update(task, description="Checking preset existence...")
        presets = _get_available_presets()
        exists = preset_name in presets
        validation_results.append(("Preset Exists", exists, None))
        progress.advance(task, 33)
        time.sleep(0.2)
        
        if not exists:
            progress.update(task, completed=100)
        else:
            # Check 2: Module loads
            progress.update(task, description="Loading server module...")
            server_class = _load_server_class(presets[preset_name])
            loads = server_class is not None
            validation_results.append(("Module Loads", loads, None))
            progress.advance(task, 33)
            time.sleep(0.2)
            
            if loads:
                # Check 3: Parameters
                progress.update(task, description="Analyzing parameters...")
                params = _parse_server_params(server_class)
                validation_results.append(("Parameters Parsed", True, f"{len(params)} parameter(s)"))
                progress.advance(task, 34)
                time.sleep(0.2)
    
    console.print()
    
    # Display results
    table = Table(
        title="Validation Results",
        box=box.ROUNDED,
        show_header=True,
        header_style=f"bold {COLORS['primary']}"
    )
    table.add_column("Check", style=COLORS["info"])
    table.add_column("Status", justify="center", width=10)
    table.add_column("Details", style=COLORS["muted"])
    
    all_passed = True
    for check_name, passed, details in validation_results:
        status = f"[{COLORS['success']}]PASS[/{COLORS['success']}]" if passed else f"[{COLORS['error']}]FAIL[/{COLORS['error']}]"
        table.add_row(check_name, status, details or "-")
        if not passed:
            all_passed = False
    
    console.print(table)
    console.print()
    
    if all_passed:
        console.print(f"[{COLORS['success']}]All validation checks passed![/{COLORS['success']}]\n")
        console.print(create_company_footer())
    else:
        console.print(f"[{COLORS['error']}]Some validation checks failed.[/{COLORS['error']}]\n")
        console.print(create_company_footer())
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()