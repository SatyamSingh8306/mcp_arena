from mcp_arena.mcp.server import BaseMCPServer
from typing import Dict, Any, List, Optional
import time
from datetime import datetime

class BaseObservabilityServer(BaseMCPServer):
    """Base class for all observability MCP servers."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics_store = {}
        self.logs_buffer = []
        self.traces_buffer = []
        
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric with timestamp."""
        timestamp = time.time()
        metric = {
            "name": name,
            "value": value,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
            "tags": tags or {}
        }
        self.metrics_store.setdefault(name, []).append(metric)
        return metric