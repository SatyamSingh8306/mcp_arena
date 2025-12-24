from typing import Optional, Dict, Any, List, Union, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import redis
from redis.exceptions import RedisError
import json
from mcp_arena.mcp.server import BaseMCPServer

@dataclass
class RedisKeyInfo:
    """Information about a Redis key."""
    key: str
    type: str
    ttl: int
    memory_usage: int
    exists: bool

@dataclass
class RedisValueInfo:
    """Information about a Redis value."""
    key: str
    value: Any
    type: str
    size: int

@dataclass
class RedisInfoSection:
    """Redis INFO command section."""
    name: str
    data: Dict[str, Any]

class RedisConnectionPoolConfig:
    """Configuration for Redis connection pool."""
    def __init__(
        self,
        max_connections: int = 10,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True
    ):
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout

class RedisMCPServer(BaseMCPServer):
    """Redis MCP Server for caching and data storage operations."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl: bool = False,
        ssl_cert_reqs: Optional[str] = None,
        connection_pool: Optional[RedisConnectionPoolConfig] = None,
        decode_responses: bool = True,
        encoding: str = "utf-8",
        mcp_host: str = "127.0.0.1",
        mcp_port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Redis MCP Server.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number (0-15)
            username: Redis username (for Redis 6+ ACL)
            password: Redis password
            ssl: Use SSL/TLS connection
            ssl_cert_reqs: SSL certificate requirements
            connection_pool: Connection pool configuration
            decode_responses: Decode responses from bytes to str
            encoding: Encoding for string responses
            mcp_host: Host to run MCP server on
            mcp_port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        # Build connection parameters
        connection_params = {
            'host': host,
            'port': port,
            'db': db,
            'decode_responses': decode_responses,
            'encoding': encoding,
            'ssl': ssl,
        }
        
        if username:
            connection_params['username'] = username
        if password:
            connection_params['password'] = password
        if ssl_cert_reqs:
            connection_params['ssl_cert_reqs'] = ssl_cert_reqs
        
        # Configure connection pool if provided
        if connection_pool:
            connection_params.update({
                'max_connections': connection_pool.max_connections,
                'socket_timeout': connection_pool.socket_timeout,
                'socket_connect_timeout': connection_pool.socket_connect_timeout,
                'retry_on_timeout': connection_pool.retry_on_timeout,
            })
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(**connection_params)
            # Test connection
            self.redis_client.ping()
            self.connected = True
        except RedisError as e:
            self.connected = False
            if debug:
                print(f"Redis connection failed: {e}")
            # Create a mock client for tool registration (actual calls will fail)
            self.redis_client = None
        
        # Initialize base class
        super().__init__(
            name="Redis MCP Server",
            description="MCP server for Redis caching and data storage operations",
            host=mcp_host,
            port=mcp_port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _check_connection(self) -> bool:
        """Check Redis connection."""
        if not self.connected or not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except RedisError:
            self.connected = False
            return False
    
    def _register_tools(self) -> None:
        """Register all Redis-related tools."""
        self._register_basic_tools()
        self._register_cache_tools()
        self._register_hash_tools()
        self._register_list_set_tools()
        self._register_server_tools()
    
    def _register_basic_tools(self):
        """Register basic key-value operations."""
        
        @self.mcp_server.tool()
        def set_key(
            key: str,
            value: str,
            expire_seconds: Optional[int] = None,
            expire_milliseconds: Optional[int] = None,
            nx: bool = False,
            xx: bool = False
        ) -> Dict[str, Any]:
            """Set a key-value pair in Redis.
            
            Args:
                key: Redis key
                value: Value to store
                expire_seconds: Expire time in seconds
                expire_milliseconds: Expire time in milliseconds
                nx: Only set if key does not exist
                xx: Only set if key exists
            """
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                # Handle expiration
                if expire_seconds:
                    result = self.redis_client.setex(key, expire_seconds, value)
                elif expire_milliseconds:
                    result = self.redis_client.psetex(key, expire_milliseconds, value)
                else:
                    if nx and xx:
                        return {"error": "Cannot use both nx and xx flags"}
                    elif nx:
                        result = self.redis_client.setnx(key, value)
                    elif xx:
                        # For XX flag, we need to check existence first
                        if self.redis_client.exists(key):
                            result = self.redis_client.set(key, value)
                        else:
                            result = None
                    else:
                        result = self.redis_client.set(key, value)
                
                return {
                    "success": bool(result),
                    "key": key,
                    "operation": "SET"
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_key(key: str) -> Dict[str, Any]:
            """Get value for a key from Redis."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                value = self.redis_client.get(key)
                if value is None:
                    return {"key": key, "exists": False}
                
                # Try to parse as JSON if it looks like JSON
                try:
                    parsed_value = json.loads(value)
                    return {
                        "key": key,
                        "value": parsed_value,
                        "type": "json",
                        "exists": True
                    }
                except json.JSONDecodeError:
                    return {
                        "key": key,
                        "value": value,
                        "type": "string",
                        "exists": True
                    }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def delete_key(key: str) -> Dict[str, Any]:
            """Delete a key from Redis."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                result = self.redis_client.delete(key)
                return {
                    "success": bool(result),
                    "deleted_count": result,
                    "key": key
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def key_exists(key: str) -> Dict[str, Any]:
            """Check if a key exists in Redis."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                exists = self.redis_client.exists(key)
                key_type = self.redis_client.type(key) if exists else None
                ttl = self.redis_client.ttl(key) if exists else -2
                
                return {
                    "exists": bool(exists),
                    "type": key_type,
                    "ttl": ttl,
                    "key": key
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_ttl(key: str) -> Dict[str, Any]:
            """Get time to live for a key in seconds."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                ttl = self.redis_client.ttl(key)
                return {
                    "key": key,
                    "ttl_seconds": ttl,
                    "status": "expires in seconds" if ttl > 0 else 
                             "no expire" if ttl == -1 else 
                             "does not exist" if ttl == -2 else "error"
                }
            except RedisError as e:
                return {"error": str(e)}
    
    def _register_cache_tools(self):
        """Register caching-specific operations."""
        
        @self.mcp_server.tool()
        def cache_get_or_set(
            key: str,
            compute_func: Optional[str] = None,
            expire_seconds: int = 3600
        ) -> Dict[str, Any]:
            """Get value from cache or compute and set if not exists.
            
            Args:
                key: Cache key
                compute_func: Optional Python expression to compute value if not cached
                expire_seconds: Cache expiration time in seconds
            """
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                # Try to get from cache
                cached = self.redis_client.get(key)
                
                if cached is not None:
                    # Return cached value
                    return {
                        "key": key,
                        "value": cached,
                        "source": "cache",
                        "cached": True
                    }
                
                # If not cached and compute_func provided
                if compute_func:
                    # In a real implementation, you'd safely evaluate the compute_func
                    # For this example, we'll simulate a computed value
                    computed_value = f"computed_for_{key}"
                    
                    # Store in cache
                    self.redis_client.setex(key, expire_seconds, computed_value)
                    
                    return {
                        "key": key,
                        "value": computed_value,
                        "source": "computed",
                        "cached": True,
                        "expires_in": expire_seconds
                    }
                else:
                    return {
                        "key": key,
                        "exists": False,
                        "source": "cache"
                    }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def cache_multi_get(keys: List[str]) -> Dict[str, Any]:
            """Get multiple values from cache in a single operation."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                values = self.redis_client.mget(keys)
                result = {}
                for i, key in enumerate(keys):
                    result[key] = {
                        "exists": values[i] is not None,
                        "value": values[i]
                    }
                
                return {"results": result}
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def cache_multi_set(
            items: Dict[str, str],
            expire_seconds: Optional[int] = None
        ) -> Dict[str, Any]:
            """Set multiple key-value pairs in cache."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                pipeline = self.redis_client.pipeline()
                
                for key, value in items.items():
                    if expire_seconds:
                        pipeline.setex(key, expire_seconds, value)
                    else:
                        pipeline.set(key, value)
                
                results = pipeline.execute()
                
                return {
                    "success": True,
                    "set_count": len(items),
                    "results": results
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def increment_counter(
            key: str,
            amount: int = 1,
            expire_seconds: Optional[int] = None
        ) -> Dict[str, Any]:
            """Increment a counter in Redis."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                if expire_seconds:
                    # Use pipeline for atomic increment with expiration
                    pipeline = self.redis_client.pipeline()
                    pipeline.incrby(key, amount)
                    pipeline.expire(key, expire_seconds)
                    results = pipeline.execute()
                    new_value = results[0]
                else:
                    new_value = self.redis_client.incrby(key, amount)
                
                return {
                    "key": key,
                    "new_value": new_value,
                    "operation": "INCR"
                }
            except RedisError as e:
                return {"error": str(e)}
    
    def _register_hash_tools(self):
        """Register hash operations."""
        
        @self.mcp_server.tool()
        def hash_set(
            key: str,
            field: str,
            value: str
        ) -> Dict[str, Any]:
            """Set field in hash."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                result = self.redis_client.hset(key, field, value)
                return {
                    "success": bool(result),
                    "key": key,
                    "field": field,
                    "operation": "HSET"
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def hash_get(
            key: str,
            field: str
        ) -> Dict[str, Any]:
            """Get field from hash."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                value = self.redis_client.hget(key, field)
                return {
                    "key": key,
                    "field": field,
                    "exists": value is not None,
                    "value": value
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def hash_get_all(key: str) -> Dict[str, Any]:
            """Get all fields and values from hash."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                all_values = self.redis_client.hgetall(key)
                return {
                    "key": key,
                    "field_count": len(all_values),
                    "data": dict(all_values)
                }
            except RedisError as e:
                return {"error": str(e)}
    
    def _register_list_set_tools(self):
        """Register list and set operations."""
        
        @self.mcp_server.tool()
        def list_push(
            key: str,
            value: str,
            side: Literal['left', 'right'] = 'right'
        ) -> Dict[str, Any]:
            """Push value to list."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                if side == 'left':
                    result = self.redis_client.lpush(key, value)
                else:
                    result = self.redis_client.rpush(key, value)
                
                return {
                    "key": key,
                    "new_length": result,
                    "operation": f"LPUSH" if side == 'left' else "RPUSH"
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def list_range(
            key: str,
            start: int = 0,
            end: int = -1
        ) -> Dict[str, Any]:
            """Get range from list."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                values = self.redis_client.lrange(key, start, end)
                return {
                    "key": key,
                    "values": values,
                    "count": len(values)
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def set_add(
            key: str,
            members: List[str]
        ) -> Dict[str, Any]:
            """Add members to set."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                result = self.redis_client.sadd(key, *members)
                return {
                    "key": key,
                    "added_count": result,
                    "operation": "SADD"
                }
            except RedisError as e:
                return {"error": str(e)}
    
    def _register_server_tools(self):
        """Register server management operations."""
        
        @self.mcp_server.tool()
        def get_redis_info(section: Optional[str] = None) -> Dict[str, Any]:
            """Get Redis server information."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                if section:
                    info = self.redis_client.info(section)
                else:
                    info = self.redis_client.info()
                
                return {
                    "server_info": info,
                    "section": section or "all"
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def flush_database(flush_all: bool = False) -> Dict[str, Any]:
            """Flush current or all databases."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                if flush_all:
                    result = self.redis_client.flushall()
                else:
                    result = self.redis_client.flushdb()
                
                return {
                    "success": bool(result),
                    "operation": "FLUSHALL" if flush_all else "FLUSHDB"
                }
            except RedisError as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def search_keys(pattern: str = "*") -> Dict[str, Any]:
            """Search for keys matching pattern."""
            if not self._check_connection():
                return {"error": "Redis connection not available"}
            
            try:
                cursor = 0
                keys = []
                
                # Use SCAN for safe iteration over large datasets
                while True:
                    cursor, partial_keys = self.redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )
                    keys.extend(partial_keys)
                    
                    if cursor == 0:
                        break
                
                # Get additional info for each key
                key_info_list = []
                for key in keys[:100]:  # Limit to 100 keys for performance
                    try:
                        key_type = self.redis_client.type(key)
                        ttl = self.redis_client.ttl(key)
                        
                        key_info = RedisKeyInfo(
                            key=key,
                            type=key_type,
                            ttl=ttl,
                            memory_usage=0,  # Would need redis-py >= 4.0 for memory usage
                            exists=True
                        )
                        key_info_list.append(asdict(key_info))
                    except:
                        continue
                
                return {
                    "pattern": pattern,
                    "total_keys": len(keys),
                    "keys": key_info_list,
                    "sample_size": min(100, len(keys))
                }
            except RedisError as e:
                return {"error": str(e)}

# Example usage
def run_redis_mcp_server():
    """Run the Redis MCP server with default configuration."""
    server = RedisMCPServer(
        host="localhost",
        port=6379,
        password=None,  # Add password if needed
        mcp_port=8001,  # Different port than S3 server
        debug=True
    )
    
    # Start the server
    server.start()
    
    return server

if __name__ == "__main__":
    # Example with custom configuration
    server = RedisMCPServer(
        host="redis.example.com",
        port=6379,
        password="your_password",
        ssl=True,
        connection_pool=RedisConnectionPoolConfig(
            max_connections=20,
            socket_timeout=10
        ),
        transport="stdio",  # For CLI integration
        debug=True
    )
    server.start()