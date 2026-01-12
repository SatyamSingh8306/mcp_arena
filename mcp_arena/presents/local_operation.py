from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import os
import sys
import json
import shutil
import subprocess
import platform
from pathlib import Path
import psutil
import socket
import webbrowser

# Handle GUI dependencies gracefully in headless environments
try:
    import pyautogui
    HAS_GUI = True
except (ImportError, KeyError, Exception) as e:
    # Handle cases where GUI is not available (CI/CD, headless environments)
    pyautogui = None
    HAS_GUI = False

from mcp_arena.mcp.server import BaseMCPServer

@dataclass
class FileInfo:
    path: str
    name: str
    size: int
    created: str
    modified: str
    accessed: str
    is_file: bool
    is_dir: bool
    is_symlink: bool
    parent: str
    suffix: str
    stem: str

@dataclass
class SystemInfo:
    system: str
    node: str
    release: str
    version: str
    machine: str
    processor: str
    python_version: str
    platform: str
    cpu_count: int
    total_memory: int
    available_memory: int

@dataclass
class ProcessInfo:
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    create_time: str
    cmdline: List[str]

@dataclass
class NetworkInfo:
    hostname: str
    ip_address: str
    mac_address: str
    interfaces: List[Dict[str, Any]]

class LocalOperationsMCPServer(BaseMCPServer):
    """Local Operations MCP Server for performing operations on the local computer."""
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        enable_system_commands: bool = True,
        enable_file_operations: bool = True,
        enable_system_info: bool = True,
        safe_mode: bool = True,
        **base_kwargs
    ):
        """Initialize Local Operations MCP Server.
        
        Args:
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            enable_system_commands: Enable system command execution tools
            enable_file_operations: Enable file operation tools
            enable_system_info: Enable system information tools
            safe_mode: Enable safety checks for dangerous operations
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.safe_mode = safe_mode
        self.enable_system_commands = enable_system_commands
        self.enable_file_operations = enable_file_operations
        self.enable_system_info = enable_system_info
        
        # Initialize base class
        super().__init__(
            name="Local Operations MCP Server",
            description="MCP server for performing operations on the local computer including file operations, system commands, and system monitoring.",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all local operation tools."""
        if self.enable_file_operations:
            self._register_file_tools()
        
        if self.enable_system_commands:
            self._register_command_tools()
        
        if self.enable_system_info:
            self._register_system_tools()
        
        self._register_process_tools()
        self._register_network_tools()
        self._register_automation_tools()
        self._register_app_tools()
    
    def _register_app_tools(self):
        """Register application launching tools."""
        
        @self.mcp_server.tool()
        def open_application(
            app_name: Annotated[str, "Application name or path"],
            arguments: Annotated[Optional[List[str]], "Command line arguments"] = None,
            wait: Annotated[bool, "Wait for app to close"] = False
        ) -> Dict[str, Any]:
            """Open an application on the local system"""
            try:
                system = platform.system()
                app_path = None
                
                # Try to find the application
                if Path(app_name).exists():
                    app_path = app_name
                else:
                    # Common applications mapping
                    app_map = {
                        "windows": {
                            "notepad": "notepad.exe",
                            "cmd": "cmd.exe",
                            "powershell": "powershell.exe",
                            "calc": "calc.exe",
                            "explorer": "explorer.exe",
                            "chrome": "chrome.exe",
                            "firefox": "firefox.exe",
                            "edge": "msedge.exe",
                            "word": "winword.exe",
                            "excel": "excel.exe",
                            "powerpoint": "powerpoint.exe",
                            "vscode": "code.exe",
                            "whatsapp": r"C:\Users\%USERNAME%\AppData\Local\WhatsApp\WhatsApp.exe",
                        },
                        "darwin": {
                            "terminal": "Terminal.app",
                            "finder": "Finder.app",
                            "calculator": "Calculator.app",
                            "safari": "Safari.app",
                            "chrome": "Google Chrome.app",
                            "firefox": "Firefox.app",
                            "notes": "Notes.app",
                            "calendar": "Calendar.app",
                            "whatsapp": "/Applications/WhatsApp.app",
                            "vscode": "/Applications/Visual Studio Code.app",
                        },
                        "linux": {
                            "terminal": ["gnome-terminal", "konsole", "xterm"],
                            "nautilus": "nautilus",
                            "firefox": "firefox",
                            "chrome": "google-chrome",
                            "gedit": "gedit",
                            "libreoffice": "libreoffice",
                            "vscode": "code",
                            "whatsapp": "whatsapp-desktop",
                        }
                    }
                    
                    os_type = system.lower()
                    if os_type == "darwin":
                        os_type = "darwin"
                    elif "linux" in os_type:
                        os_type = "linux"
                    elif "windows" in os_type:
                        os_type = "windows"
                    
                    if os_type in app_map:
                        if app_name.lower() in app_map[os_type]:
                            app_path = app_map[os_type][app_name.lower()]
                            
                            # Handle Linux app lists
                            if isinstance(app_path, list):
                                for possible_app in app_path:
                                    try:
                                        subprocess.run(["which", possible_app], 
                                                     capture_output=True, check=True)
                                        app_path = possible_app
                                        break
                                    except:
                                        continue
                
                if not app_path:
                    # Try to find in PATH
                    try:
                        if system == "Windows":
                            result = subprocess.run(["where", app_name], 
                                                  capture_output=True, text=True)
                        else:
                            result = subprocess.run(["which", app_name], 
                                                  capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            app_path = result.stdout.strip().split('\n')[0]
                    except:
                        pass
                
                if not app_path:
                    return {"error": f"Application '{app_name}' not found"}
                
                # Launch the application
                cmd = [app_path]
                if arguments:
                    cmd.extend(arguments)
                
                if system == "Windows":
                    # On Windows, use START command for GUI apps
                    if not app_path.endswith('.exe') or app_name.lower() in ['cmd', 'powershell']:
                        process = subprocess.Popen(cmd)
                    else:
                        full_cmd = f'start "" "{app_path}"'
                        if arguments:
                            full_cmd += f' {" ".join(arguments)}'
                        process = subprocess.Popen(full_cmd, shell=True)
                else:
                    # On Unix-like systems
                    process = subprocess.Popen(cmd)
                
                pid = process.pid if hasattr(process, 'pid') else None
                
                if wait:
                    process.wait()
                    return_code = process.returncode
                else:
                    return_code = None
                
                return {
                    "success": True,
                    "app_name": app_name,
                    "app_path": app_path,
                    "pid": pid,
                    "return_code": return_code,
                    "waited": wait,
                    "arguments": arguments
                }
            except Exception as e:
                return {"error": f"Failed to open application: {str(e)}"}
        
        @self.mcp_server.tool()
        def list_installed_apps(
            category: Annotated[Optional[str], "Filter by category"] = None
        ) -> Dict[str, Any]:
            """List installed applications"""
            try:
                system = platform.system()
                apps = []
                
                if system == "Windows":
                    # Windows: Query registry for installed programs
                    import winreg
                    
                    registry_paths = [
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
                    ]
                    
                    for reg_path in registry_paths:
                        try:
                            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                            for i in range(0, winreg.QueryInfoKey(key)[0]):
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    subkey = winreg.OpenKey(key, subkey_name)
                                    
                                    app_name = None
                                    try:
                                        app_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    except:
                                        continue
                                    
                                    if app_name:
                                        install_location = None
                                        try:
                                            install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                        except:
                                            pass
                                        
                                        display_version = None
                                        try:
                                            display_version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                                        except:
                                            pass
                                        
                                        apps.append({
                                            "name": app_name,
                                            "version": display_version,
                                            "install_location": install_location,
                                            "registry_key": subkey_name
                                        })
                                except:
                                    continue
                        except:
                            continue
                
                elif system == "Darwin":  # macOS
                    # macOS: Check /Applications and ~/Applications
                    app_dirs = [
                        "/Applications",
                        os.path.expanduser("~/Applications")
                    ]
                    
                    for app_dir in app_dirs:
                        if os.path.exists(app_dir):
                            for item in os.listdir(app_dir):
                                if item.endswith('.app'):
                                    app_path = os.path.join(app_dir, item)
                                    app_name = item.replace('.app', '')
                                    
                                    # Get app info from Info.plist
                                    info_plist = os.path.join(app_path, 'Contents', 'Info.plist')
                                    version = "Unknown"
                                    if os.path.exists(info_plist):
                                        try:
                                            import plistlib
                                            with open(info_plist, 'rb') as f:
                                                plist_data = plistlib.load(f)
                                                version = plist_data.get('CFBundleShortVersionString', 'Unknown')
                                        except:
                                            pass
                                    
                                    apps.append({
                                        "name": app_name,
                                        "version": version,
                                        "path": app_path,
                                        "type": "app"
                                    })
                
                elif system == "Linux":
                    # Linux: Check common directories and dpkg/rpm
                    app_dirs = [
                        "/usr/share/applications",
                        "/usr/local/share/applications",
                        os.path.expanduser("~/.local/share/applications")
                    ]
                    
                    for app_dir in app_dirs:
                        if os.path.exists(app_dir):
                            for file in os.listdir(app_dir):
                                if file.endswith('.desktop'):
                                    desktop_file = os.path.join(app_dir, file)
                                    try:
                                        with open(desktop_file, 'r') as f:
                                            content = f.read()
                                        
                                        # Parse .desktop file
                                        app_name = None
                                        exec_cmd = None
                                        version = "Unknown"
                                        
                                        for line in content.split('\n'):
                                            if line.startswith('Name='):
                                                app_name = line[5:].strip()
                                            elif line.startswith('Exec='):
                                                exec_cmd = line[5:].strip()
                                            elif line.startswith('Version='):
                                                version = line[8:].strip()
                                        
                                        if app_name and exec_cmd:
                                            apps.append({
                                                "name": app_name,
                                                "version": version,
                                                "exec": exec_cmd,
                                                "desktop_file": file
                                            })
                                    except:
                                        continue
                
                # Filter by category if specified
                if category:
                    filtered_apps = []
                    for app in apps:
                        app_name_lower = app["name"].lower()
                        if category.lower() in app_name_lower:
                            filtered_apps.append(app)
                    apps = filtered_apps
                
                return {
                    "system": system,
                    "applications": apps[:100],  # Limit to first 100
                    "count": len(apps),
                    "filtered": category is not None
                }
            except Exception as e:
                return {"error": f"Failed to list installed apps: {str(e)}"}
        
        @self.mcp_server.tool()
        def open_terminal(
            command: Annotated[Optional[str], "Command to execute in terminal"] = None,
            working_dir: Annotated[Optional[str], "Working directory"] = None
        ) -> Dict[str, Any]:
            """Open a terminal window"""
            try:
                system = platform.system()
                
                if system == "Windows":
                    if command:
                        # Open cmd with command
                        full_cmd = f'cmd /k "{command}"'
                        if working_dir:
                            full_cmd = f'cd /d "{working_dir}" && {full_cmd}'
                        subprocess.Popen(full_cmd, shell=True)
                    else:
                        # Open cmd
                        if working_dir:
                            subprocess.Popen(f'start cmd /k "cd /d "{working_dir}""', shell=True)
                        else:
                            subprocess.Popen('start cmd', shell=True)
                
                elif system == "Darwin":  # macOS
                    if command:
                        apple_script = f'''
                        tell application "Terminal"
                            do script "{command}"
                            activate
                        end tell
                        '''
                        subprocess.Popen(['osascript', '-e', apple_script])
                    else:
                        subprocess.Popen(['open', '-a', 'Terminal'])
                
                elif system == "Linux":
                    # Try different terminals
                    terminals = ['gnome-terminal', 'konsole', 'xterm', 'terminator', 'xfce4-terminal']
                    
                    for terminal in terminals:
                        try:
                            result = subprocess.run(["which", terminal], 
                                                  capture_output=True, text=True)
                            if result.returncode == 0:
                                cmd = [terminal]
                                if command:
                                    if terminal == 'gnome-terminal':
                                        cmd.extend(['--', 'bash', '-c', command])
                                    elif terminal == 'konsole':
                                        cmd.extend(['-e', 'bash', '-c', command])
                                    else:
                                        cmd.extend(['-e', command])
                                subprocess.Popen(cmd)
                                break
                        except:
                            continue
                
                return {
                    "success": True,
                    "terminal_opened": True,
                    "system": system,
                    "command": command,
                    "working_dir": working_dir
                }
            except Exception as e:
                return {"error": f"Failed to open terminal: {str(e)}"}
        
        @self.mcp_server.tool()
        def open_file_explorer(
            path: Annotated[Optional[str], "Path to open in file explorer"] = None
        ) -> Dict[str, Any]:
            """Open file explorer at a specific path"""
            try:
                system = platform.system()
                
                if not path:
                    path = os.path.expanduser("~")  # Open home directory by default
                
                path = Path(path).expanduser().resolve()
                
                if not path.exists():
                    return {"error": f"Path does not exist: {path}"}
                
                if system == "Windows":
                    subprocess.Popen(f'explorer "{path}"')
                elif system == "Darwin":  # macOS
                    subprocess.Popen(['open', str(path)])
                elif system == "Linux":
                    # Try different file managers
                    file_managers = ['nautilus', 'dolphin', 'thunar', 'pcmanfm', 'nemo']
                    
                    for fm in file_managers:
                        try:
                            result = subprocess.run(["which", fm], 
                                                  capture_output=True, text=True)
                            if result.returncode == 0:
                                subprocess.Popen([fm, str(path)])
                                break
                        except:
                            continue
                
                return {
                    "success": True,
                    "path": str(path),
                    "system": system
                }
            except Exception as e:
                return {"error": f"Failed to open file explorer: {str(e)}"}
        
        @self.mcp_server.tool()
        def open_web_browser(
            url: Annotated[str, "URL to open"],
            browser: Annotated[Optional[str], "Browser to use: chrome, firefox, safari, edge"] = None
        ) -> Dict[str, Any]:
            """Open URL in a specific web browser"""
            try:
                system = platform.system()
                
                browser_map = {
                    "chrome": {
                        "windows": "chrome.exe",
                        "darwin": "Google Chrome.app",
                        "linux": "google-chrome"
                    },
                    "firefox": {
                        "windows": "firefox.exe",
                        "darwin": "Firefox.app",
                        "linux": "firefox"
                    },
                    "safari": {
                        "darwin": "Safari.app"
                    },
                    "edge": {
                        "windows": "msedge.exe",
                        "darwin": "Microsoft Edge.app"
                    }
                }
                
                if browser:
                    browser_lower = browser.lower()
                    if browser_lower in browser_map:
                        os_type = "windows" if system == "Windows" else "darwin" if system == "Darwin" else "linux"
                        
                        if os_type in browser_map[browser_lower]:
                            browser_cmd = browser_map[browser_lower][os_type]
                            
                            if system == "Windows":
                                subprocess.Popen(f'start "" "{browser_cmd}" "{url}"', shell=True)
                            elif system == "Darwin":
                                subprocess.Popen(['open', '-a', browser_cmd, url])
                            elif system == "Linux":
                                subprocess.Popen([browser_cmd, url])
                        else:
                            # Browser not available on this OS, use default
                            webbrowser.open(url)
                    else:
                        # Invalid browser specified, use default
                        webbrowser.open(url)
                else:
                    # Use default browser
                    webbrowser.open(url)
                
                return {
                    "success": True,
                    "url": url,
                    "browser": browser if browser else "default",
                    "system": system
                }
            except Exception as e:
                return {"error": f"Failed to open web browser: {str(e)}"}

    def _register_file_tools(self):
        """Register file system operation tools."""
        
        @self.mcp_server.tool()
        def list_directory(
            path: Annotated[str, "Directory path"] = ".",
            show_hidden: Annotated[bool, "Show hidden files"] = False,
            recursive: Annotated[bool, "List recursively"] = False
        ) -> Dict[str, Any]:
            """List contents of a directory"""
            try:
                base_path = Path(path).expanduser().resolve()
                if not base_path.exists():
                    return {"error": f"Path does not exist: {path}"}
                if not base_path.is_dir():
                    return {"error": f"Path is not a directory: {path}"}
                
                items = []
                if recursive:
                    for item_path in base_path.rglob("*"):
                        if not show_hidden and item_path.name.startswith('.'):
                            continue
                        try:
                            items.append(self._get_file_info_dict(item_path))
                        except (PermissionError, OSError):
                            continue
                else:
                    for item_path in base_path.iterdir():
                        if not show_hidden and item_path.name.startswith('.'):
                            continue
                        try:
                            items.append(self._get_file_info_dict(item_path))
                        except (PermissionError, OSError):
                            continue
                
                return {
                    "path": str(base_path),
                    "items": items,
                    "count": len(items),
                    "recursive": recursive
                }
            except Exception as e:
                return {"error": f"Failed to list directory: {str(e)}"}
        
        @self.mcp_server.tool()
        def read_file(
            filepath: Annotated[str, "Path to file"],
            encoding: Annotated[str, "File encoding"] = "utf-8",
            limit_lines: Annotated[Optional[int], "Maximum number of lines to read"] = None
        ) -> Dict[str, Any]:
            """Read contents of a file"""
            try:
                path = Path(filepath).expanduser().resolve()
                if not path.exists():
                    return {"error": f"File does not exist: {filepath}"}
                if not path.is_file():
                    return {"error": f"Path is not a file: {filepath}"}
                
                file_info = self._get_file_info_dict(path)
                
                with open(path, 'r', encoding=encoding) as f:
                    if limit_lines:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= limit_lines:
                                break
                            lines.append(line.rstrip('\n'))
                        content = '\n'.join(lines)
                    else:
                        content = f.read()
                
                return {
                    "file_info": file_info,
                    "content": content,
                    "encoding": encoding,
                    "size": len(content)
                }
            except Exception as e:
                return {"error": f"Failed to read file: {str(e)}"}
        
        @self.mcp_server.tool()
        def write_file(
            filepath: Annotated[str, "Path to file"],
            content: Annotated[str, "Content to write"],
            encoding: Annotated[str, "File encoding"] = "utf-8",
            mode: Annotated[str, "Write mode: 'w' for write, 'a' for append"] = "w",
            create_dirs: Annotated[bool, "Create parent directories if they don't exist"] = True
        ) -> Dict[str, Any]:
            """Write content to a file"""
            try:
                if self.safe_mode and mode == 'w':
                    path = Path(filepath).expanduser()
                    if path.exists():
                        return {
                            "error": "File already exists. Use mode='a' to append or disable safe_mode.",
                            "file_exists": True
                        }
                
                path = Path(filepath).expanduser()
                if create_dirs:
                    path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(path, mode, encoding=encoding) as f:
                    f.write(content)
                
                return {
                    "success": True,
                    "filepath": str(path),
                    "size": len(content),
                    "mode": mode,
                    "created": not path.exists() and mode == 'w'
                }
            except Exception as e:
                return {"error": f"Failed to write file: {str(e)}"}
        
        @self.mcp_server.tool()
        def copy_file(
            source: Annotated[str, "Source file path"],
            destination: Annotated[str, "Destination file path"],
            overwrite: Annotated[bool, "Overwrite if destination exists"] = False
        ) -> Dict[str, Any]:
            """Copy a file"""
            try:
                src = Path(source).expanduser().resolve()
                dst = Path(destination).expanduser()
                
                if not src.exists():
                    return {"error": f"Source file does not exist: {source}"}
                if not src.is_file():
                    return {"error": f"Source is not a file: {source}"}
                
                if dst.exists() and not overwrite:
                    return {"error": f"Destination file already exists: {destination}"}
                
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                
                return {
                    "success": True,
                    "source": str(src),
                    "destination": str(dst),
                    "size": src.stat().st_size
                }
            except Exception as e:
                return {"error": f"Failed to copy file: {str(e)}"}
        
        @self.mcp_server.tool()
        def delete_file(
            filepath: Annotated[str, "Path to file"],
            confirm: Annotated[bool, "Require confirmation"] = True
        ) -> Dict[str, Any]:
            """Delete a file"""
            try:
                if self.safe_mode and confirm:
                    return {
                        "warning": "Safe mode requires confirmation. Call again with confirm=False",
                        "file_info": self._get_file_info_dict(Path(filepath).expanduser())
                    }
                
                path = Path(filepath).expanduser().resolve()
                if not path.exists():
                    return {"error": f"File does not exist: {filepath}"}
                
                file_info = self._get_file_info_dict(path)
                path.unlink()
                
                return {
                    "success": True,
                    "deleted_file": file_info
                }
            except Exception as e:
                return {"error": f"Failed to delete file: {str(e)}"}
    
    def _register_command_tools(self):
        """Register system command execution tools."""
        
        @self.mcp_server.tool()
        def execute_command(
            command: Annotated[str, "Command to execute"],
            working_dir: Annotated[Optional[str], "Working directory"] = None,
            timeout: Annotated[Optional[int], "Timeout in seconds"] = 30,
            shell: Annotated[bool, "Use shell execution"] = True
        ) -> Dict[str, Any]:
            """Execute a system command"""
            try:
                if self.safe_mode:
                    dangerous_commands = ['rm -rf', 'format', 'mkfs', 'dd']
                    if any(cmd in command.lower() for cmd in dangerous_commands):
                        return {"error": "Command contains dangerous operations. Disable safe_mode to execute."}
                
                cwd = None
                if working_dir:
                    cwd = Path(working_dir).expanduser()
                    if not cwd.exists() or not cwd.is_dir():
                        return {"error": f"Invalid working directory: {working_dir}"}
                
                result = subprocess.run(
                    command,
                    shell=shell,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                return {
                    "command": command,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0,
                    "timeout": False
                }
            except subprocess.TimeoutExpired:
                return {
                    "command": command,
                    "error": "Command timed out",
                    "timeout": True
                }
            except Exception as e:
                return {"error": f"Failed to execute command: {str(e)}"}
        
        @self.mcp_server.tool()
        def get_environment() -> Dict[str, Any]:
            """Get environment variables"""
            try:
                env_vars = dict(os.environ)
                # Filter out sensitive information in safe mode
                if self.safe_mode:
                    sensitive_keys = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'PASS']
                    for key in list(env_vars.keys()):
                        if any(sensitive in key.upper() for sensitive in sensitive_keys):
                            env_vars[key] = '[REDACTED]'
                
                return {
                    "environment_variables": env_vars,
                    "count": len(env_vars),
                    "platform": platform.system()
                }
            except Exception as e:
                return {"error": f"Failed to get environment: {str(e)}"}
    
    def _register_system_tools(self):
        """Register system information tools."""
        
        @self.mcp_server.tool()
        def get_system_info() -> Dict[str, Any]:
            """Get detailed system information"""
            try:
                sys_info = SystemInfo(
                    system=platform.system(),
                    node=platform.node(),
                    release=platform.release(),
                    version=platform.version(),
                    machine=platform.machine(),
                    processor=platform.processor(),
                    python_version=platform.python_version(),
                    platform=platform.platform(),
                    cpu_count=psutil.cpu_count(),
                    total_memory=psutil.virtual_memory().total,
                    available_memory=psutil.virtual_memory().available
                )
                
                # Get disk information
                disk_partitions = []
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_partitions.append({
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype,
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent
                        })
                    except (PermissionError, OSError):
                        continue
                
                return {
                    "system_info": asdict(sys_info),
                    "disk_partitions": disk_partitions,
                    "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                    "uptime": datetime.now() - datetime.fromtimestamp(psutil.boot_time())
                }
            except Exception as e:
                return {"error": f"Failed to get system info: {str(e)}"}
        
        @self.mcp_server.tool()
        def get_cpu_info() -> Dict[str, Any]:
            """Get CPU information and usage"""
            try:
                cpu_times = psutil.cpu_times()
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_percent_per_core = psutil.cpu_percent(interval=1, percpu=True)
                cpu_freq = psutil.cpu_freq()
                cpu_stats = psutil.cpu_stats()
                
                return {
                    "cpu_count": psutil.cpu_count(),
                    "cpu_count_logical": psutil.cpu_count(logical=True),
                    "cpu_percent": cpu_percent,
                    "cpu_percent_per_core": cpu_percent_per_core,
                    "cpu_times": {
                        "user": cpu_times.user,
                        "system": cpu_times.system,
                        "idle": cpu_times.idle,
                        "nice": getattr(cpu_times, 'nice', 0)
                    },
                    "cpu_frequency": {
                        "current": getattr(cpu_freq, 'current', None),
                        "min": getattr(cpu_freq, 'min', None),
                        "max": getattr(cpu_freq, 'max', None)
                    } if cpu_freq else None,
                    "cpu_stats": {
                        "ctx_switches": cpu_stats.ctx_switches,
                        "interrupts": cpu_stats.interrupts,
                        "soft_interrupts": cpu_stats.soft_interrupts,
                        "syscalls": cpu_stats.syscalls
                    }
                }
            except Exception as e:
                return {"error": f"Failed to get CPU info: {str(e)}"}
        
        @self.mcp_server.tool()
        def get_memory_info() -> Dict[str, Any]:
            """Get memory information"""
            try:
                virtual_memory = psutil.virtual_memory()
                swap_memory = psutil.swap_memory()
                
                return {
                    "virtual_memory": {
                        "total": virtual_memory.total,
                        "available": virtual_memory.available,
                        "used": virtual_memory.used,
                        "free": virtual_memory.free,
                        "percent": virtual_memory.percent
                    },
                    "swap_memory": {
                        "total": swap_memory.total,
                        "used": swap_memory.used,
                        "free": swap_memory.free,
                        "percent": swap_memory.percent,
                        "sin": swap_memory.sin,
                        "sout": swap_memory.sout
                    }
                }
            except Exception as e:
                return {"error": f"Failed to get memory info: {str(e)}"}
    
    def _register_process_tools(self):
        """Register process management tools."""
        
        @self.mcp_server.tool()
        def list_processes(
            limit: Annotated[Optional[int], "Maximum number of processes to return"] = 50
        ) -> Dict[str, Any]:
            """List running processes"""
            try:
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                                'memory_percent', 'create_time', 'cmdline']):
                    try:
                        proc_info = proc.info
                        process_info = ProcessInfo(
                            pid=proc_info['pid'],
                            name=proc_info['name'],
                            status=proc_info['status'],
                            cpu_percent=proc_info.get('cpu_percent', 0),
                            memory_percent=proc_info.get('memory_percent', 0),
                            create_time=datetime.fromtimestamp(proc_info['create_time']).isoformat(),
                            cmdline=proc_info.get('cmdline', [])
                        )
                        processes.append(asdict(process_info))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Sort by CPU usage descending
                processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                
                return {
                    "processes": processes[:limit] if limit else processes,
                    "count": len(processes),
                    "limited": limit is not None and len(processes) > limit
                }
            except Exception as e:
                return {"error": f"Failed to list processes: {str(e)}"}
        
        @self.mcp_server.tool()
        def kill_process(
            pid: Annotated[int, "Process ID"],
            signal: Annotated[str, "Signal to send: SIGTERM or SIGKILL"] = "SIGTERM"
        ) -> Dict[str, Any]:
            """Kill a process"""
            try:
                if self.safe_mode:
                    return {
                        "error": "Safe mode prevents killing processes. Disable safe_mode to proceed.",
                        "pid": pid
                    }
                
                proc = psutil.Process(pid)
                
                if signal.upper() == "SIGKILL":
                    proc.kill()
                else:
                    proc.terminate()
                
                return {
                    "success": True,
                    "pid": pid,
                    "signal": signal,
                    "process_name": proc.name()
                }
            except psutil.NoSuchProcess:
                return {"error": f"Process with PID {pid} does not exist"}
            except Exception as e:
                return {"error": f"Failed to kill process: {str(e)}"}
    
    def _register_network_tools(self):
        """Register network operation tools."""
        
        @self.mcp_server.tool()
        def get_network_info() -> Dict[str, Any]:
            """Get network information"""
            try:
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                
                interfaces = []
                for interface, addrs in psutil.net_if_addrs().items():
                    interface_info = {
                        "interface": interface,
                        "addresses": []
                    }
                    for addr in addrs:
                        interface_info["addresses"].append({
                            "family": str(addr.family),
                            "address": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast
                        })
                    interfaces.append(interface_info)
                
                net_info = NetworkInfo(
                    hostname=hostname,
                    ip_address=ip_address,
                    mac_address=self._get_mac_address(),
                    interfaces=interfaces
                )
                
                return asdict(net_info)
            except Exception as e:
                return {"error": f"Failed to get network info: {str(e)}"}
        
        @self.mcp_server.tool()
        def check_connectivity(
            host: Annotated[str, "Host to check connectivity"],
            port: Annotated[Optional[int], "Port to check"] = None,
            timeout: Annotated[int, "Timeout in seconds"] = 5
        ) -> Dict[str, Any]:
            """Check network connectivity"""
            try:
                if port:
                    # Check specific port
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    return {
                        "host": host,
                        "port": port,
                        "reachable": result == 0,
                        "latency": "N/A"
                    }
                else:
                    # Check general connectivity
                    import time
                    start = time.time()
                    try:
                        socket.gethostbyname(host)
                        latency = time.time() - start
                        return {
                            "host": host,
                            "reachable": True,
                            "latency": round(latency * 1000, 2)  # Convert to ms
                        }
                    except socket.gaierror:
                        return {
                            "host": host,
                            "reachable": False,
                            "latency": None
                        }
            except Exception as e:
                return {"error": f"Failed to check connectivity: {str(e)}"}
    
    def _register_automation_tools(self):
        """Register UI automation tools."""
        
        @self.mcp_server.tool()
        def take_screenshot(
            save_path: Annotated[Optional[str], "Path to save screenshot"] = None
        ) -> Dict[str, Any]:
            """Take a screenshot of the screen"""
            if not HAS_GUI:
                return {"error": "GUI operations not available in headless environment"}
            
            try:
                screenshot = pyautogui.screenshot()
                
                if save_path:
                    path = Path(save_path).expanduser()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    screenshot.save(path)
                
                return {
                    "success": True,
                    "size": screenshot.size,
                    "mode": screenshot.mode,
                    "saved_path": save_path if save_path else None
                }
            except Exception as e:
                return {"error": f"Failed to take screenshot: {str(e)}"}
        
        @self.mcp_server.tool()
        def get_screen_info() -> Dict[str, Any]:
            """Get screen information"""
            if not HAS_GUI:
                return {"error": "GUI operations not available in headless environment"}
            
            try:
                screen_size = pyautogui.size()
                mouse_position = pyautogui.position()
                
                return {
                    "screen_width": screen_size.width,
                    "screen_height": screen_size.height,
                    "mouse_x": mouse_position.x,
                    "mouse_y": mouse_position.y,
                    "pixel_scale": pyautogui.pixel(mouse_position.x, mouse_position.y)
                }
            except Exception as e:
                return {"error": f"Failed to get screen info: {str(e)}"}
        
        @self.mcp_server.tool()
        def open_browser(
            url: Annotated[str, "URL to open in browser"],
            new_tab: Annotated[bool, "Open in new tab"] = True
        ) -> Dict[str, Any]:
            """Open URL in default web browser"""
            try:
                webbrowser.open(url, new=new_tab)
                
                return {
                    "success": True,
                    "url": url,
                    "new_tab": new_tab
                }
            except Exception as e:
                return {"error": f"Failed to open browser: {str(e)}"}
    
    # Helper methods
    def _get_file_info_dict(self, path: Path) -> Dict[str, Any]:
        """Convert Path to file info dictionary"""
        stat = path.stat()
        return {
            "path": str(path.absolute()),
            "name": path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
            "parent": str(path.parent),
            "suffix": path.suffix,
            "stem": path.stem,
        }
    
    def _get_mac_address(self) -> str:
        """Get MAC address of primary network interface"""
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == psutil.AF_LINK:
                        return addr.address
            return "Unknown"
        except:
            return "Unknown"

# Example usage
if __name__ == "__main__":
    server = LocalOperationsMCPServer(
        host="127.0.0.1",
        port=8000,
        transport="stdio",
        debug=True,
        enable_system_commands=True,
        enable_file_operations=True,
        enable_system_info=True,
        safe_mode=True  # Enable safety checks
    )
    
    # Run the server
    server.run()