from typing import Any, Dict, List, Optional
from .interfaces import IAgentPolicy


class BasePolicy(IAgentPolicy):
    """Base implementation for agent policies"""
    
    def __init__(self, name: str):
        self.name = name
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Default implementation allows all actions"""
        return True
    
    def filter_response(self, response: Any) -> Any:
        """Default implementation returns response unchanged"""
        return response


class SafetyPolicy(BasePolicy):
    """Policy to ensure safe and appropriate responses"""
    
    def __init__(self):
        super().__init__("safety")
        # List of potentially harmful keywords
        self.harmful_keywords = [
            "hack", "exploit", "malware", "virus", "illegal", 
            "harmful", "dangerous", "weapon", "violence"
        ]
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate that actions don't contain harmful content"""
        action_str = str(action).lower()
        
        for keyword in self.harmful_keywords:
            if keyword in action_str:
                return False
        
        return True
    
    def filter_response(self, response: Any) -> Any:
        """Filter out potentially harmful content from responses"""
        if not isinstance(response, str):
            return response
        
        response_lower = response.lower()
        
        # Check for harmful content
        for keyword in self.harmful_keywords:
            if keyword in response_lower:
                return "I cannot provide information on that topic for safety reasons."
        
        return response


class ContentFilterPolicy(BasePolicy):
    """Policy to filter and moderate content"""
    
    def __init__(self, max_length: int = 5000, blocked_words: List[str] = None):
        super().__init__("content_filter")
        self.max_length = max_length
        self.blocked_words = blocked_words or []
    
    def filter_response(self, response: Any) -> Any:
        """Filter response content"""
        if not isinstance(response, str):
            return response
        
        # Length filtering
        if len(response) > self.max_length:
            response = response[:self.max_length] + "... (truncated)"
        
        # Word filtering
        for word in self.blocked_words:
            response = response.replace(word, "*" * len(word))
        
        return response


class RateLimitPolicy(BasePolicy):
    """Policy to implement rate limiting"""
    
    def __init__(self, max_requests_per_minute: int = 60):
        super().__init__("rate_limit")
        self.max_requests = max_requests_per_minute
        self.request_times: List[float] = []
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Check if action is within rate limits"""
        import time
        
        current_time = time.time()
        
        # Remove old requests (older than 1 minute)
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < 60
        ]
        
        # Check if we're at the limit
        if len(self.request_times) >= self.max_requests:
            return False
        
        # Add current request
        self.request_times.append(current_time)
        return True
    
    def filter_response(self, response: Any) -> Any:
        """Add rate limiting information to response"""
        if isinstance(response, str) and len(self.request_times) > self.max_requests * 0.8:
            response += "\n\n(Note: Approaching rate limit)"
        
        return response


class LoggingPolicy(BasePolicy):
    """Policy to log agent actions and responses"""
    
    def __init__(self, log_file: str = "agent_logs.txt"):
        super().__init__("logging")
        self.log_file = log_file
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Log action validation"""
        self._log(f"ACTION_VALIDATION: {action}")
        return True
    
    def filter_response(self, response: Any) -> Any:
        """Log response filtering"""
        self._log(f"RESPONSE: {str(response)[:200]}...")  # Log first 200 chars
        return response
    
    def _log(self, message: str) -> None:
        """Write message to log file"""
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Silently fail logging to avoid breaking agent


class PrivacyPolicy(BasePolicy):
    """Policy to protect sensitive information"""
    
    def __init__(self):
        super().__init__("privacy")
        # Patterns that might indicate sensitive information
        self.sensitive_patterns = [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{1,5}\s+\w+\s+\w+\b',  # Address pattern
        ]
    
    def filter_response(self, response: Any) -> Any:
        """Filter out sensitive information"""
        if not isinstance(response, str):
            return response
        
        import re
        
        filtered_response = response
        
        # Apply all sensitive patterns
        for pattern in self.sensitive_patterns:
            filtered_response = re.sub(pattern, '[REDACTED]', filtered_response, flags=re.IGNORECASE)
        
        return filtered_response


class ToolUsagePolicy(BasePolicy):
    """Policy to control tool usage"""
    
    def __init__(self, allowed_tools: List[str] = None, max_tool_calls: int = 10):
        super().__init__("tool_usage")
        self.allowed_tools = allowed_tools or []
        self.max_tool_calls = max_tool_calls
        self.tool_call_count = 0
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate tool usage"""
        # Check tool call count
        if self.tool_call_count >= self.max_tool_calls:
            return False
        
        # Check if tool is allowed
        if "tool" in action:
            tool_name = action["tool"]
            if self.allowed_tools and tool_name not in self.allowed_tools:
                return False
            
            self.tool_call_count += 1
        
        return True
    
    def filter_response(self, response: Any) -> Any:
        """Add tool usage information to response"""
        if isinstance(response, str) and self.tool_call_count > 0:
            response += f"\n\n(Tools used: {self.tool_call_count}/{self.max_tool_calls})"
        
        return response


class PolicyChain:
    """Chain of policies for complex policy management"""
    
    def __init__(self):
        self.policies: List[IAgentPolicy] = []
    
    def add_policy(self, policy: IAgentPolicy) -> None:
        """Add a policy to the chain"""
        self.policies.append(policy)
    
    def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy by name"""
        for i, policy in enumerate(self.policies):
            if hasattr(policy, 'name') and policy.name == policy_name:
                del self.policies[i]
                return True
        return False
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate action through all policies"""
        for policy in self.policies:
            if not policy.validate_action(action):
                return False
        return True
    
    def filter_response(self, response: Any) -> Any:
        """Filter response through all policies"""
        filtered_response = response
        for policy in self.policies:
            filtered_response = policy.filter_response(filtered_response)
        return filtered_response
    
    def list_policies(self) -> List[str]:
        """List all policy names"""
        names = []
        for policy in self.policies:
            if hasattr(policy, 'name'):
                names.append(policy.name)
            else:
                names.append(policy.__class__.__name__)
        return names


def create_default_policy_chain() -> PolicyChain:
    """Create a default chain of policies"""
    chain = PolicyChain()
    chain.add_policy(SafetyPolicy())
    chain.add_policy(PrivacyPolicy())
    chain.add_policy(ContentFilterPolicy(max_length=5000))
    return chain


def create_restricted_policy_chain() -> PolicyChain:
    """Create a more restrictive policy chain"""
    chain = PolicyChain()
    chain.add_policy(SafetyPolicy())
    chain.add_policy(PrivacyPolicy())
    chain.add_policy(ContentFilterPolicy(max_length=2000))
    chain.add_policy(RateLimitPolicy(max_requests_per_minute=30))
    chain.add_policy(ToolUsagePolicy(max_tool_calls=5))
    return chain