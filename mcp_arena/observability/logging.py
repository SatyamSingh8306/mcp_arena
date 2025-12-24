import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from mcp_arena.mcp.server import BaseMCPServer

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogEntry:
    timestamp: str
    level: LogLevel
    message: str
    server_name: str
    server_type: str
    tool_name: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    duration_ms: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class MCPLogger:
    """Structured logger for MCP servers."""
    
    def __init__(self, server_name: str, server_type: str, log_file: Optional[str] = None):
        self.server_name = server_name
        self.server_type = server_type
        self.session_id = f"session_{int(datetime.now().timestamp())}"
        
        # Configure logging
        self.logger = logging.getLogger(f"mcp.{server_name}")
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
        
        self.log_buffer: List[LogEntry] = []
        self.max_buffer_size = 1000
    
    def log(
        self,
        level: LogLevel,
        message: str,
        tool_name: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogEntry:
        """Create a structured log entry."""
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
            server_name=self.server_name,
            server_type=self.server_type,
            tool_name=tool_name,
            user_id=user_id,
            session_id=self.session_id,
            request_id=request_id,
            duration_ms=duration_ms,
            error_details=error_details,
            metadata=metadata
        )
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > self.max_buffer_size:
            self.log_buffer = self.log_buffer[-self.max_buffer_size:]
        
        # Also log to standard logging
        log_method = getattr(self.logger, level.value.lower())
        log_msg = f"{message}"
        if tool_name:
            log_msg = f"[{tool_name}] {log_msg}"
        if duration_ms is not None:
            log_msg = f"{log_msg} (took {duration_ms}ms)"
        
        log_method(log_msg)
        
        return log_entry
    
    def debug(self, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> LogEntry:
        return self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        tool_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get logs with optional filtering."""
        filtered_logs = self.log_buffer
        
        if level:
            filtered_logs = [log for log in filtered_logs if log.level == level]
        if tool_name:
            filtered_logs = [log for log in filtered_logs if log.tool_name == tool_name]
        
        return [asdict(log) for log in filtered_logs[-limit:]]
    
    def export_logs(self, filepath: str) -> None:
        """Export logs to JSON file."""
        logs_data = [asdict(log) for log in self.log_buffer]
        with open(filepath, 'w') as f:
            json.dump(logs_data, f, indent=2)

class LoggingMCPServer(BaseMCPServer):
    """MCP server for centralized logging across all MCP servers."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="MCP Logging Server",
            description="Centralized logging for all MCP servers",
            **kwargs
        )
        self.server_loggers: Dict[str, MCPLogger] = {}
        self.global_log_buffer: List[LogEntry] = []
        self.max_global_buffer = 10000
    
    def _register_tools(self):
        """Register logging tools."""
        
        @self.mcp_server.tool()
        def register_server_logger(
            server_name: str,
            server_type: str
        ) -> Dict[str, Any]:
            """Register an MCP server for centralized logging."""
            logger = MCPLogger(server_name, server_type)
            self.server_loggers[server_name] = logger
            
            # Hook into the logger to capture all logs
            original_log = logger.log
            
            def hooked_log(*args, **kwargs):
                entry = original_log(*args, **kwargs)
                # Also store in global buffer
                self.global_log_buffer.append(entry)
                if len(self.global_log_buffer) > self.max_global_buffer:
                    self.global_log_buffer = self.global_log_buffer[-self.max_global_buffer:]
                return entry
            
            logger.log = hooked_log
            
            return {
                "success": True,
                "server": server_name,
                "logger_id": id(logger),
                "message": f"Logger registered for {server_name}"
            }
        
        @self.mcp_server.tool()
        def search_logs(
            query: Optional[str] = None,
            server_name: Optional[str] = None,
            level: Optional[str] = None,
            tool_name: Optional[str] = None,
            time_range: str = "last_1h",
            limit: int = 100
        ) -> Dict[str, Any]:
            """Search logs across all registered servers."""
            from datetime import datetime, timedelta
            
            # Parse time range
            cutoff = self._parse_time_range(time_range)
            
            filtered_logs = []
            for log in self.global_log_buffer:
                log_time = datetime.fromisoformat(log.timestamp)
                
                # Apply filters
                if log_time < cutoff:
                    continue
                if server_name and log.server_name != server_name:
                    continue
                if level and log.level.value != level.upper():
                    continue
                if tool_name and log.tool_name != tool_name:
                    continue
                if query and query.lower() not in log.message.lower():
                    continue
                
                filtered_logs.append(asdict(log))
            
            return {
                "logs": filtered_logs[-limit:],
                "total_matched": len(filtered_logs),
                "showing": min(limit, len(filtered_logs)),
                "query": query,
                "filters": {
                    "server_name": server_name,
                    "level": level,
                    "tool_name": tool_name,
                    "time_range": time_range
                }
            }
        
        @self.mcp_server.tool()
        def get_server_logs(
            server_name: str,
            level: Optional[str] = None,
            limit: int = 50
        ) -> Dict[str, Any]:
            """Get logs for a specific server."""
            if server_name not in self.server_loggers:
                return {"error": f"Server '{server_name}' not registered for logging"}
            
            logger = self.server_loggers[server_name]
            logs = logger.get_logs(
                level=LogLevel(level) if level else None,
                limit=limit
            )
            
            return {
                "server": server_name,
                "logs": logs,
                "count": len(logs),
                "buffer_size": len(logger.log_buffer)
            }
        
        @self.mcp_server.tool()
        def analyze_tool_performance(
            server_name: Optional[str] = None,
            tool_name: Optional[str] = None
        ) -> Dict[str, Any]:
            """Analyze performance of tools based on log durations."""
            relevant_logs = []
            for log in self.global_log_buffer:
                if log.duration_ms is None:
                    continue
                if server_name and log.server_name != server_name:
                    continue
                if tool_name and log.tool_name != tool_name:
                    continue
                relevant_logs.append(log)
            
            if not relevant_logs:
                return {"message": "No performance data available"}
            
            # Calculate statistics
            durations = [log.duration_ms for log in relevant_logs if log.duration_ms]
            if durations:
                stats = {
                    "count": len(durations),
                    "avg_ms": sum(durations) / len(durations),
                    "min_ms": min(durations),
                    "max_ms": max(durations),
                    "total_calls": len(relevant_logs),
                    "sample_logs": [asdict(log) for log in relevant_logs[-5:]]
                }
                
                # Identify slowest tools
                tool_durations = {}
                for log in relevant_logs:
                    if log.tool_name and log.duration_ms:
                        tool_durations.setdefault(log.tool_name, []).append(log.duration_ms)
                
                slowest_tools = []
                for tool, times in tool_durations.items():
                    slowest_tools.append({
                        "tool": tool,
                        "avg_time": sum(times) / len(times),
                        "call_count": len(times)
                    })
                
                slowest_tools.sort(key=lambda x: x["avg_time"], reverse=True)
                
                stats["slowest_tools"] = slowest_tools[:10]
                return stats
            
            return {"message": "No duration data available"}
    
    def _parse_time_range(self, time_range: str) -> datetime:
        """Parse time range string to datetime."""
        from datetime import timedelta
        
        now = datetime.now()
        
        if time_range == "last_15m":
            return now - timedelta(minutes=15)
        elif time_range == "last_1h":
            return now - timedelta(hours=1)
        elif time_range == "last_24h":
            return now - timedelta(hours=24)
        elif time_range == "last_7d":
            return now - timedelta(days=7)
        else:
            # Default to 1 hour
            return now - timedelta(hours=1)