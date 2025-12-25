from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
import docker
import json
import subprocess
import sys
from pathlib import Path
from enum import Enum
from mcp_arena.mcp.server import BaseMCPServer

class ContainerStatus(Enum):
    """Container status enumeration."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"

class ContainerState(Enum):
    """Container state enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"

@dataclass
class ContainerInfo:
    """Information about a Docker container."""
    id: str
    name: str
    image: str
    status: str
    state: str
    created: str
    ports: List[Dict[str, str]]
    networks: List[str]
    command: str
    labels: Dict[str, str]
    env: List[str]
    mounts: List[Dict[str, str]]
    host_config: Dict[str, Any]
    
@dataclass
class ImageInfo:
    """Information about a Docker image."""
    id: str
    tags: List[str]
    created: str
    size: int
    virtual_size: int
    labels: Dict[str, str]
    
@dataclass
class NetworkInfo:
    """Information about a Docker network."""
    id: str
    name: str
    driver: str
    scope: str
    ipam: Dict[str, Any]
    containers: Dict[str, Any]
    labels: Dict[str, str]
    
@dataclass
class VolumeInfo:
    """Information about a Docker volume."""
    name: str
    driver: str
    mountpoint: str
    labels: Dict[str, str]
    options: Dict[str, str]
    scope: str
    
@dataclass
class ContainerStats:
    """Container statistics."""
    container_id: str
    name: str
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_rx: int
    network_tx: int
    block_read: int
    block_write: int
    pids: int
    timestamp: str
    
@dataclass
class ContainerLogs:
    """Container logs."""
    container_id: str
    name: str
    logs: List[str]
    stdout_count: int
    stderr_count: int
    timestamp: str

class DockerMCPServer(BaseMCPServer):
    """Docker MCP Server for container and image management."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        version: str = "auto",
        timeout: int = 60,
        tls_config: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        credstore_env: Optional[Dict[str, str]] = None,
        use_ssh_client: bool = False,
        max_pool_size: int = 10,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Docker MCP Server.
        
        Args:
            base_url: Docker daemon URL (e.g., unix://var/run/docker.sock, tcp://localhost:2375)
            version: API version (default: "auto")
            timeout: Timeout for API calls in seconds
            tls_config: TLS configuration for remote connections
            user_agent: Custom user agent string
            credstore_env: Credential store environment variables
            use_ssh_client: Use SSH client for connections
            max_pool_size: Maximum connection pool size
            host: Host to run MCP server on
            port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        # Initialize Docker client with provided configuration
        client_params = {}
        
        if base_url:
            client_params['base_url'] = base_url
        if version:
            client_params['version'] = version
        if timeout:
            client_params['timeout'] = timeout
        if tls_config:
            client_params['tls'] = docker.tls.TLSConfig(**tls_config)
        if user_agent:
            client_params['user_agent'] = user_agent
        if credstore_env:
            client_params['credstore_env'] = credstore_env
        if use_ssh_client:
            client_params['use_ssh_client'] = use_ssh_client
        if max_pool_size:
            client_params['max_pool_size'] = max_pool_size
        
        try:
            self.docker_client = docker.from_env(**client_params) if not client_params else docker.DockerClient(**client_params)
            # Test connection
            self.docker_client.ping()
            self.connected = True
            self.api_client = docker.APIClient(**client_params) if not client_params else docker.APIClient(**client_params)
        except Exception as e:
            self.connected = False
            self.docker_client = None
            self.api_client = None
            if debug:
                print(f"Docker connection failed: {e}")
        
        # Initialize base class
        super().__init__(
            name="Docker MCP Server",
            description="MCP server for Docker container and image management",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _check_connection(self) -> bool:
        """Check Docker daemon connection."""
        if not self.connected or not self.docker_client:
            return False
        try:
            self.docker_client.ping()
            return True
        except Exception:
            self.connected = False
            return False
    
    def _parse_container_info(self, container) -> ContainerInfo:
        """Parse container object into ContainerInfo dataclass."""
        container.reload()  # Refresh container data
        
        # Parse ports
        ports = []
        if container.ports:
            for private_port, port_mappings in container.ports.items():
                if port_mappings:
                    for mapping in port_mappings if isinstance(port_mappings, list) else [port_mappings]:
                        ports.append({
                            "private_port": private_port,
                            "public_port": mapping.get('HostPort', ''),
                            "host_ip": mapping.get('HostIp', '0.0.0.0')
                        })
        
        # Parse networks
        networks = list(container.attrs['NetworkSettings']['Networks'].keys()) if container.attrs.get('NetworkSettings', {}).get('Networks') else []
        
        # Parse mounts
        mounts = []
        if container.attrs.get('Mounts'):
            for mount in container.attrs['Mounts']:
                mounts.append({
                    "source": mount.get('Source', ''),
                    "destination": mount.get('Destination', ''),
                    "type": mount.get('Type', ''),
                    "mode": mount.get('Mode', '')
                })
        
        # Parse environment variables
        env = container.attrs.get('Config', {}).get('Env', [])
        
        return ContainerInfo(
            id=container.id[:12],
            name=container.name,
            image=container.image.tags[0] if container.image.tags else container.image.id[:12],
            status=container.status,
            state=container.status.split()[0].lower() if container.status else "unknown",
            created=container.attrs['Created'],
            ports=ports,
            networks=networks,
            command=container.attrs['Config'].get('Cmd', '') or container.attrs['Config'].get('Entrypoint', ''),
            labels=container.labels or {},
            env=env,
            mounts=mounts,
            host_config=container.attrs.get('HostConfig', {})
        )
    
    def _parse_image_info(self, image) -> ImageInfo:
        """Parse image object into ImageInfo dataclass."""
        return ImageInfo(
            id=image.id[7:19] if image.id.startswith('sha256:') else image.id[:12],
            tags=image.tags,
            created=image.attrs['Created'],
            size=image.attrs['Size'],
            virtual_size=image.attrs.get('VirtualSize', image.attrs['Size']),
            labels=image.labels or {}
        )
    
    def _register_tools(self) -> None:
        """Register all Docker-related tools."""
        self._register_container_tools()
        self._register_image_tools()
        self._register_network_tools()
        self._register_volume_tools()
        self._register_system_tools()
        self._register_compose_tools()
    
    def _register_container_tools(self):
        """Register container management tools."""
        
        @self.mcp_server.tool()
        def list_containers(
            all: bool = False,
            filters: Optional[str] = None
        ) -> Dict[str, Any]:
            """List Docker containers.
            
            Args:
                all: Show all containers (default shows just running)
                filters: JSON string of filter conditions
            """
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                # Parse filters if provided
                filter_dict = json.loads(filters) if filters else {}
                
                containers = self.docker_client.containers.list(
                    all=all,
                    filters=filter_dict
                )
                
                container_list = []
                for container in containers:
                    try:
                        container_info = self._parse_container_info(container)
                        container_list.append(asdict(container_info))
                    except Exception as e:
                        if self.debug:
                            print(f"Error parsing container {container.id}: {e}")
                        continue
                
                return {
                    "count": len(container_list),
                    "containers": container_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def run_container(
            image: str,
            name: Optional[str] = None,
            command: Optional[str] = None,
            ports: Optional[Dict[str, str]] = None,
            volumes: Optional[Dict[str, Dict[str, str]]] = None,
            environment: Optional[Dict[str, str]] = None,
            network: Optional[str] = None,
            network_mode: Optional[str] = None,
            detach: bool = True,
            remove: bool = False,
            auto_remove: bool = False,
            restart_policy: Optional[Dict[str, str]] = None,
            labels: Optional[Dict[str, str]] = None,
            working_dir: Optional[str] = None,
            entrypoint: Optional[str] = None,
            cpu_shares: Optional[int] = None,
            mem_limit: Optional[str] = None,
            memswap_limit: Optional[str] = None
        ) -> Dict[str, Any]:
            """Run a new Docker container.
            
            Args:
                image: Docker image name and tag
                name: Container name (optional)
                command: Command to run in container
                ports: Port mappings (host:container)
                volumes: Volume mappings
                environment: Environment variables
                network: Network to connect to
                network_mode: Network mode (bridge, host, none)
                detach: Run in background
                remove: Remove container when it stops
                auto_remove: Automatically remove container when it exits
                restart_policy: Restart policy (e.g., {"Name": "always"})
                labels: Container labels
                working_dir: Working directory inside container
                entrypoint: Entrypoint command
                cpu_shares: CPU shares (relative weight)
                mem_limit: Memory limit (e.g., "512m")
                memswap_limit: Total memory + swap limit
            """
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                # Parse command if provided as string
                cmd_list = command.split() if command else None
                
                # Parse environment variables
                env_list = None
                if environment:
                    env_list = [f"{k}={v}" for k, v in environment.items()]
                
                # Run container
                container = self.docker_client.containers.run(
                    image=image,
                    name=name,
                    command=cmd_list,
                    ports=ports,
                    volumes=volumes,
                    environment=env_list,
                    network=network,
                    network_mode=network_mode,
                    detach=detach,
                    remove=remove,
                    auto_remove=auto_remove,
                    restart_policy=restart_policy,
                    labels=labels,
                    working_dir=working_dir,
                    entrypoint=entrypoint,
                    cpu_shares=cpu_shares,
                    mem_limit=mem_limit,
                    memswap_limit=memswap_limit
                )
                
                # Get container info
                container_info = self._parse_container_info(container)
                
                return {
                    "success": True,
                    "container": asdict(container_info),
                    "message": f"Container '{container.name}' started successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def start_container(container_id: str) -> Dict[str, Any]:
            """Start a stopped Docker container."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                container.start()
                container_info = self._parse_container_info(container)
                
                return {
                    "success": True,
                    "container": asdict(container_info),
                    "message": f"Container '{container.name}' started successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def stop_container(
            container_id: str,
            timeout: int = 10
        ) -> Dict[str, Any]:
            """Stop a running Docker container."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                container.stop(timeout=timeout)
                container_info = self._parse_container_info(container)
                
                return {
                    "success": True,
                    "container": asdict(container_info),
                    "message": f"Container '{container.name}' stopped successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def restart_container(
            container_id: str,
            timeout: int = 10
        ) -> Dict[str, Any]:
            """Restart a Docker container."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                container.restart(timeout=timeout)
                container_info = self._parse_container_info(container)
                
                return {
                    "success": True,
                    "container": asdict(container_info),
                    "message": f"Container '{container.name}' restarted successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def remove_container(
            container_id: str,
            force: bool = False,
            v: bool = False
        ) -> Dict[str, Any]:
            """Remove a Docker container.
            
            Args:
                container_id: Container ID or name
                force: Force removal (stop if running)
                v: Remove associated volumes
            """
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                container_name = container.name
                container.remove(force=force, v=v)
                
                return {
                    "success": True,
                    "message": f"Container '{container_name}' removed successfully"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def inspect_container(container_id: str) -> Dict[str, Any]:
            """Get detailed information about a container."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                container_info = self._parse_container_info(container)
                
                return {
                    "container": asdict(container_info),
                    "raw_attrs": container.attrs
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_container_logs(
            container_id: str,
            tail: int = 100,
            follow: bool = False,
            stdout: bool = True,
            stderr: bool = True,
            timestamps: bool = False
        ) -> Dict[str, Any]:
            """Get logs from a container.
            
            Args:
                container_id: Container ID or name
                tail: Number of lines to show from the end
                follow: Follow log output
                stdout: Include stdout
                stderr: Include stderr
                timestamps: Show timestamps
            """
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                
                if follow:
                    # For follow mode, we return a stream description
                    return {
                        "container_id": container.id[:12],
                        "name": container.name,
                        "follow": True,
                        "message": "Log following started. Use stop_follow_logs to stop.",
                        "instructions": "This is a streaming operation. The logs will continue until stopped."
                    }
                else:
                    # Get logs
                    logs = container.logs(
                        tail=tail,
                        stdout=stdout,
                        stderr=stderr,
                        timestamps=timestamps
                    ).decode('utf-8').splitlines()
                    
                    return ContainerLogs(
                        container_id=container.id[:12],
                        name=container.name,
                        logs=logs,
                        stdout_count=len([l for l in logs if not l.startswith('[stderr]')]),
                        stderr_count=len([l for l in logs if l.startswith('[stderr]')]),
                        timestamp=datetime.now().isoformat()
                    ).__dict__
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def exec_command(
            container_id: str,
            command: str,
            workdir: Optional[str] = None,
            user: Optional[str] = None,
            environment: Optional[Dict[str, str]] = None,
            detach: bool = False,
            tty: bool = False
        ) -> Dict[str, Any]:
            """Execute a command in a running container."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                
                # Prepare exec configuration
                exec_config = {
                    'cmd': command.split(),
                    'workdir': workdir,
                    'user': user,
                    'environment': environment,
                    'detach': detach,
                    'tty': tty
                }
                
                # Remove None values
                exec_config = {k: v for k, v in exec_config.items() if v is not None}
                
                # Execute command
                result = container.exec_run(**exec_config)
                
                if detach:
                    return {
                        "success": True,
                        "exec_id": result.id,
                        "detached": True,
                        "message": f"Command executed in detached mode in container '{container.name}'"
                    }
                else:
                    output = result.output.decode('utf-8') if result.output else ""
                    return {
                        "success": result.exit_code == 0,
                        "exit_code": result.exit_code,
                        "output": output,
                        "container": container.name,
                        "command": command
                    }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_container_stats(container_id: str) -> Dict[str, Any]:
            """Get real-time statistics for a container."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                container = self.docker_client.containers.get(container_id)
                stats = container.stats(stream=False)
                
                # Parse CPU stats
                cpu_stats = stats.get('cpu_stats', {})
                precpu_stats = stats.get('precpu_stats', {})
                
                cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                           precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
                system_delta = cpu_stats.get('system_cpu_usage', 0) - \
                              precpu_stats.get('system_cpu_usage', 0)
                
                cpu_percent = 0.0
                if system_delta > 0 and cpu_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100.0
                
                # Parse memory stats
                memory_stats = stats.get('memory_stats', {})
                memory_usage = memory_stats.get('usage', 0)
                memory_limit = memory_stats.get('limit', 0)
                memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0
                
                # Parse network stats
                networks = stats.get('networks', {})
                network_rx = 0
                network_tx = 0
                for iface_stats in networks.values():
                    network_rx += iface_stats.get('rx_bytes', 0)
                    network_tx += iface_stats.get('tx_bytes', 0)
                
                # Parse block I/O stats
                blkio_stats = stats.get('blkio_stats', {})
                block_read = 0
                block_write = 0
                for stat in blkio_stats.get('io_service_bytes_recursive', []):
                    if stat.get('op') == 'Read':
                        block_read += stat.get('value', 0)
                    elif stat.get('op') == 'Write':
                        block_write += stat.get('value', 0)
                
                return ContainerStats(
                    container_id=container.id[:12],
                    name=container.name,
                    cpu_percent=round(cpu_percent, 2),
                    memory_usage=memory_usage,
                    memory_limit=memory_limit,
                    memory_percent=round(memory_percent, 2),
                    network_rx=network_rx,
                    network_tx=network_tx,
                    block_read=block_read,
                    block_write=block_write,
                    pids=stats.get('pids_stats', {}).get('current', 0),
                    timestamp=stats.get('read', datetime.now().isoformat())
                ).__dict__
            except Exception as e:
                return {"error": str(e)}
    
    def _register_image_tools(self):
        """Register image management tools."""
        
        @self.mcp_server.tool()
        def list_images(all: bool = True) -> Dict[str, Any]:
            """List Docker images."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                images = self.docker_client.images.list(all=all)
                
                image_list = []
                for image in images:
                    image_info = self._parse_image_info(image)
                    image_list.append(asdict(image_info))
                
                return {
                    "count": len(image_list),
                    "images": image_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def pull_image(
            repository: str,
            tag: str = "latest",
            auth_config: Optional[Dict[str, str]] = None
        ) -> Dict[str, Any]:
            """Pull a Docker image from a registry."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                # Pull image with progress tracking
                full_image = f"{repository}:{tag}"
                
                # For simplicity, we'll use a basic pull
                # In production, you'd want to handle progress callbacks
                image = self.docker_client.images.pull(
                    repository=repository,
                    tag=tag,
                    auth_config=auth_config
                )
                
                image_info = self._parse_image_info(image)
                
                return {
                    "success": True,
                    "image": asdict(image_info),
                    "message": f"Successfully pulled {full_image}"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def remove_image(
            image_id: str,
            force: bool = False,
            noprune: bool = False
        ) -> Dict[str, Any]:
            """Remove a Docker image."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                # Try to get image by ID first, then by name/tag
                try:
                    image = self.docker_client.images.get(image_id)
                except:
                    # Try as repository:tag
                    image = self.docker_client.images.get(image_id)
                
                tags = image.tags
                self.docker_client.images.remove(
                    image=image_id,
                    force=force,
                    noprune=noprune
                )
                
                return {
                    "success": True,
                    "removed_tags": tags,
                    "message": f"Successfully removed image {image_id}"
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def build_image(
            path: str,
            tag: str,
            dockerfile: str = "Dockerfile",
            buildargs: Optional[Dict[str, str]] = None,
            labels: Optional[Dict[str, str]] = None,
            nocache: bool = False,
            rm: bool = True,
            forcerm: bool = False,
            pull: bool = False
        ) -> Dict[str, Any]:
            """Build a Docker image from a Dockerfile."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                # Build image
                image, build_logs = self.docker_client.images.build(
                    path=path,
                    tag=tag,
                    dockerfile=dockerfile,
                    buildargs=buildargs,
                    labels=labels,
                    nocache=nocache,
                    rm=rm,
                    forcerm=forcerm,
                    pull=pull
                )
                
                # Parse build logs
                log_entries = []
                for chunk in build_logs:
                    if 'stream' in chunk:
                        log_entries.append(chunk['stream'].strip())
                    elif 'error' in chunk:
                        log_entries.append(f"ERROR: {chunk['error']}")
                
                image_info = self._parse_image_info(image)
                
                return {
                    "success": True,
                    "image": asdict(image_info),
                    "build_logs": log_entries[-50:],  # Last 50 lines
                    "message": f"Successfully built {tag}"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_network_tools(self):
        """Register network management tools."""
        
        @self.mcp_server.tool()
        def list_networks() -> Dict[str, Any]:
            """List Docker networks."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                networks = self.docker_client.networks.list()
                
                network_list = []
                for network in networks:
                    network_info = NetworkInfo(
                        id=network.id[:12],
                        name=network.name,
                        driver=network.attrs.get('Driver', 'bridge'),
                        scope=network.attrs.get('Scope', 'local'),
                        ipam=network.attrs.get('IPAM', {}),
                        containers=network.attrs.get('Containers', {}),
                        labels=network.attrs.get('Labels', {})
                    )
                    network_list.append(asdict(network_info))
                
                return {
                    "count": len(network_list),
                    "networks": network_list
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def create_network(
            name: str,
            driver: str = "bridge",
            options: Optional[Dict[str, str]] = None,
            ipam: Optional[Dict[str, Any]] = None,
            check_duplicate: bool = True,
            internal: bool = False,
            labels: Optional[Dict[str, str]] = None,
            enable_ipv6: bool = False,
            attachable: bool = False,
            scope: str = "local"
        ) -> Dict[str, Any]:
            """Create a Docker network."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                network = self.docker_client.networks.create(
                    name=name,
                    driver=driver,
                    options=options,
                    ipam=ipam,
                    check_duplicate=check_duplicate,
                    internal=internal,
                    labels=labels,
                    enable_ipv6=enable_ipv6,
                    attachable=attachable,
                    scope=scope
                )
                
                network_info = NetworkInfo(
                    id=network.id[:12],
                    name=network.name,
                    driver=network.attrs.get('Driver', driver),
                    scope=network.attrs.get('Scope', scope),
                    ipam=network.attrs.get('IPAM', {}),
                    containers=network.attrs.get('Containers', {}),
                    labels=network.attrs.get('Labels', labels or {})
                )
                
                return {
                    "success": True,
                    "network": asdict(network_info),
                    "message": f"Network '{name}' created successfully"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_volume_tools(self):
        """Register volume management tools."""
        
        @self.mcp_server.tool()
        def list_volumes() -> Dict[str, Any]:
            """List Docker volumes."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                volumes = self.docker_client.volumes.list()
                
                volume_list = []
                for volume in volumes:
                    volume_info = VolumeInfo(
                        name=volume.name,
                        driver=volume.attrs['Driver'],
                        mountpoint=volume.attrs['Mountpoint'],
                        labels=volume.attrs.get('Labels', {}),
                        options=volume.attrs.get('Options', {}),
                        scope=volume.attrs.get('Scope', 'local')
                    )
                    volume_list.append(asdict(volume_info))
                
                return {
                    "count": len(volume_list),
                    "volumes": volume_list
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_system_tools(self):
        """Register system management tools."""
        
        @self.mcp_server.tool()
        def system_info() -> Dict[str, Any]:
            """Get Docker system information."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                info = self.docker_client.info()
                version = self.docker_client.version()
                
                return {
                    "info": info,
                    "version": version
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def system_prune(
            all: bool = False,
            volumes: bool = False
        ) -> Dict[str, Any]:
            """Remove unused Docker data."""
            if not self._check_connection():
                return {"error": "Docker connection not available"}
            
            try:
                result = self.docker_client.containers.prune()
                result_images = self.docker_client.images.prune()
                result_networks = self.docker_client.networks.prune()
                
                volumes_pruned = {}
                if volumes:
                    result_volumes = self.docker_client.volumes.prune()
                    volumes_pruned = result_volumes
                
                return {
                    "success": True,
                    "containers_pruned": result,
                    "images_pruned": result_images,
                    "networks_pruned": result_networks,
                    "volumes_pruned": volumes_pruned,
                    "message": "System prune completed"
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_compose_tools(self):
        """Register Docker Compose tools."""
        
        @self.mcp_server.tool()
        def compose_up(
            path: str = ".",
            services: Optional[List[str]] = None,
            detach: bool = True,
            build: bool = False,
            no_build: bool = False,
            force_recreate: bool = False,
            no_recreate: bool = False,
            renew_anon_volumes: bool = False,
            remove_orphans: bool = False
        ) -> Dict[str, Any]:
            """Start Docker Compose services.
            
            Note: This uses docker-compose CLI if available, or Docker SDK's compose support.
            """
            try:
                # Check if docker-compose is available
                compose_command = ["docker-compose"]
                
                # For Docker Desktop with compose v2
                try:
                    subprocess.run(["docker", "compose", "version"], 
                                 capture_output=True, check=True)
                    compose_command = ["docker", "compose"]
                except:
                    pass
                
                # Build command
                cmd = compose_command + ["up"]
                
                if detach:
                    cmd.append("-d")
                if build:
                    cmd.append("--build")
                if no_build:
                    cmd.append("--no-build")
                if force_recreate:
                    cmd.append("--force-recreate")
                if no_recreate:
                    cmd.append("--no-recreate")
                if renew_anon_volumes:
                    cmd.append("-V")
                if remove_orphans:
                    cmd.append("--remove-orphans")
                if services:
                    cmd.extend(services)
                
                # Run command
                result = subprocess.run(
                    cmd,
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "command": " ".join(cmd)
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def compose_down(
            path: str = ".",
            volumes: bool = False,
            remove_orphans: bool = False,
            timeout: Optional[int] = None
        ) -> Dict[str, Any]:
            """Stop and remove Docker Compose services."""
            try:
                # Check if docker-compose is available
                compose_command = ["docker-compose"]
                
                # For Docker Desktop with compose v2
                try:
                    subprocess.run(["docker", "compose", "version"], 
                                 capture_output=True, check=True)
                    compose_command = ["docker", "compose"]
                except:
                    pass
                
                # Build command
                cmd = compose_command + ["down"]
                
                if volumes:
                    cmd.append("-v")
                if remove_orphans:
                    cmd.append("--remove-orphans")
                if timeout:
                    cmd.extend(["-t", str(timeout)])
                
                # Run command
                result = subprocess.run(
                    cmd,
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout
                )
                
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "command": " ".join(cmd)
                }
            except Exception as e:
                return {"error": str(e)}


# Example usage and runner
def run_docker_mcp_server():
    """Run the Docker MCP server with default configuration."""
    server = DockerMCPServer(
        # Connect to default Docker socket
        base_url="unix://var/run/docker.sock",
        mcp_port=8003,  # Different port than Redis/S3 servers
        debug=True
    )
    
    # Start the server
    server.start()
    
    return server


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Docker MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="MCP server host")
    parser.add_argument("--port", type=int, default=8003, help="MCP server port")
    parser.add_argument("--docker-url", help="Docker daemon URL")
    parser.add_argument("--transport", default="stdio", choices=['stdio', 'sse', 'streamable-http'],
                       help="Transport type")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    server = DockerMCPServer(
        base_url=args.docker_url,
        host=args.host,
        port=args.port,
        transport=args.transport,
        debug=args.debug
    )
    
    print(f"Starting Docker MCP Server on {args.host}:{args.port}")
    print(f"Docker URL: {args.docker_url or 'default'}")
    print(f"Transport: {args.transport}")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down Docker MCP Server...")
    except Exception as e:
        print(f"Error: {e}")