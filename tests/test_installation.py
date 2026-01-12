"""Test installation and package configuration."""

import pytest
import subprocess
import sys
import importlib
from pathlib import Path


class TestPackageInstallation:
    """Test package installation and configuration."""

    def test_package_import(self):
        """Test that mcp_arena package can be imported."""
        try:
            import mcp_arena
            assert mcp_arena is not None
            assert hasattr(mcp_arena, '__version__')
        except ImportError as e:
            pytest.fail(f"Failed to import mcp_arena: {e}")

    def test_package_version(self):
        """Test package version is available and valid."""
        import mcp_arena
        
        version = getattr(mcp_arena, '__version__', None)
        assert version is not None, "Package version not set"
        assert isinstance(version, str), "Version should be a string"
        assert len(version) > 0, "Version should not be empty"

    def test_package_metadata(self):
        """Test package metadata is available."""
        import mcp_arena
        
        # Check common package attributes
        metadata_attrs = ['__author__', '__license__', '__description__']
        
        for attr in metadata_attrs:
            if hasattr(mcp_arena, attr):
                value = getattr(mcp_arena, attr)
                assert value is not None, f"Package attribute {attr} is None"
                assert isinstance(value, str), f"Package attribute {attr} should be a string"

    def test_package_structure(self):
        """Test package structure is correct."""
        import mcp_arena
        
        # Check main submodules exist
        expected_submodules = [
            'mcp',
            'agent', 
            'presents',
            'tools',
            'cli'
        ]
        
        for submodule in expected_submodules:
            try:
                importlib.import_module(f'mcp_arena.{submodule}')
            except ImportError as e:
                pytest.fail(f"Failed to import submodule mcp_arena.{submodule}: {e}")


class TestOptionalDependencies:
    """Test optional dependencies installation."""

    def test_core_dependencies_available(self):
        """Test core dependencies are available."""
        core_deps = [
            'mcp',
            'python_dotenv',
            'typing_extensions',
            'psutil',
            'langchain',
            'langchain_core',
            'typer',
            'rich'
        ]
        
        for dep in core_deps:
            try:
                importlib.import_module(dep.replace('-', '_'))
            except ImportError:
                pytest.fail(f"Core dependency '{dep}' not available")

    def test_communication_dependencies_groups(self):
        """Test communication dependency groups."""
        communication_groups = {
            'gmail': ['google.auth', 'googleapiclient'],
            'outlook': ['msal'],
            'slack': ['slack_sdk'],
            'whatsapp': ['twilio']
        }
        
        for service, deps in communication_groups.items():
            available_deps = []
            for dep in deps:
                try:
                    importlib.import_module(dep.replace('-', '_'))
                    available_deps.append(dep)
                except ImportError:
                    pass
            
            # At least one dependency should be available for each service
            if len(available_deps) == 0:
                pytest.warn(f"No dependencies available for {service}: {deps}")

    def test_database_dependencies_groups(self):
        """Test database dependency groups."""
        database_groups = {
            'postgres': ['psycopg2'],
            'mongo': ['pymongo'],
            'redis': ['redis'],
            'docker': ['docker']
        }
        
        for service, deps in database_groups.items():
            available_deps = []
            for dep in deps:
                try:
                    importlib.import_module(dep)
                    available_deps.append(dep)
                except ImportError:
                    pass
            
            # At least one dependency should be available for each service
            if len(available_deps) == 0:
                pytest.warn(f"No dependencies available for {service}: {deps}")

    def test_cloud_dependencies_groups(self):
        """Test cloud service dependency groups."""
        cloud_groups = {
            'github': ['github'],
            'aws': ['boto3'],
            'notion': ['notion_client'],
            'gitlab': ['gitlab'],
            'bitbucket': ['atlassian'],
            'jira': ['jira'],
            'confluence': ['atlassian']
        }
        
        for service, deps in cloud_groups.items():
            available_deps = []
            for dep in deps:
                try:
                    importlib.import_module(dep)
                    available_deps.append(dep)
                except ImportError:
                    pass
            
            # At least one dependency should be available for each service
            if len(available_deps) == 0:
                pytest.warn(f"No dependencies available for {service}: {deps}")


class TestInstallationCommands:
    """Test installation commands and pip extras."""

    def test_pip_show_command(self):
        """Test pip show command works for mcp_arena."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', 'mcp_arena'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should succeed (exit code 0) or fail gracefully if not installed
            if result.returncode == 0:
                assert 'mcp_arena' in result.stdout
                assert 'Version:' in result.stdout
            else:
                pytest.warn(f"mcp_arena not installed via pip: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            pytest.warn("pip show command timed out")
        except Exception as e:
            pytest.warn(f"Error running pip show: {e}")

    def test_pip_list_contains_mcp_arena(self):
        """Test pip list contains mcp_arena."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                assert 'mcp_arena' in result.stdout.lower()
            else:
                pytest.warn(f"pip list command failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            pytest.warn("pip list command timed out")
        except Exception as e:
            pytest.warn(f"Error running pip list: {e}")

    def test_package_entry_points(self):
        """Test package entry points are available."""
        try:
            # Check if CLI entry point is available
            from mcp_arena.cli import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"CLI entry point not available: {e}")

    def test_package_console_scripts(self):
        """Test package console scripts are available."""
        try:
            # Try to run the CLI command
            result = subprocess.run(
                [sys.executable, '-m', 'mcp_arena.cli', '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should succeed or fail gracefully
            if result.returncode == 0:
                assert 'Usage:' in result.stdout or 'usage:' in result.stdout
            else:
                pytest.warn(f"CLI command failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            pytest.warn("CLI command timed out")
        except Exception as e:
            pytest.warn(f"Error running CLI command: {e}")


class TestConfigurationFiles:
    """Test configuration files and setup."""

    def test_pyproject_toml_exists(self):
        """Test pyproject.toml exists and is readable."""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / 'pyproject.toml'
        
        assert pyproject_path.exists(), "pyproject.toml not found"
        assert pyproject_path.is_file(), "pyproject.toml is not a file"
        
        # Try to read it
        try:
            content = pyproject_path.read_text(encoding='utf-8')
            assert len(content) > 0, "pyproject.toml is empty"
            assert '[project]' in content, "pyproject.toml missing [project] section"
            assert 'name = "mcp_arena"' in content, "pyproject.toml missing project name"
        except Exception as e:
            pytest.fail(f"Error reading pyproject.toml: {e}")

    def test_pyproject_toml_optional_dependencies(self):
        """Test pyproject.toml has optional dependencies defined."""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / 'pyproject.toml'
        
        try:
            content = pyproject_path.read_text(encoding='utf-8')
            
            # Check for communication services
            communication_services = ['gmail', 'outlook', 'slack', 'whatsapp']
            for service in communication_services:
                assert f'{service} = [' in content, f"Optional dependency {service} not defined"
            
            # Check for groups
            assert 'email = [' in content, "Email group not defined"
            assert 'messaging = [' in content, "Messaging group not defined"
            assert 'communication = [' in content, "Communication group not defined"
            
        except Exception as e:
            pytest.fail(f"Error checking pyproject.toml optional dependencies: {e}")

    def test_requirements_txt_exists(self):
        """Test requirements.txt exists and is readable."""
        project_root = Path(__file__).parent.parent
        requirements_path = project_root / 'requirements.txt'
        
        if requirements_path.exists():
            try:
                content = requirements_path.read_text(encoding='utf-8')
                # Should have some content
                assert len(content.strip()) > 0, "requirements.txt is empty"
            except Exception as e:
                pytest.fail(f"Error reading requirements.txt: {e}")

    def test_setup_py_or_cfg_exists(self):
        """Test setup.py or setup.cfg exists if used."""
        project_root = Path(__file__).parent.parent
        setup_py = project_root / 'setup.py'
        setup_cfg = project_root / 'setup.cfg'
        
        # At least one should exist if pyproject.toml doesn't handle everything
        if not (project_root / 'pyproject.toml').exists():
            assert setup_py.exists() or setup_cfg.exists(), "Neither setup.py nor setup.cfg found"


class TestInstallationIntegrity:
    """Test installation integrity and consistency."""

    def test_all_modules_importable(self):
        """Test all expected modules can be imported."""
        expected_modules = [
            'mcp_arena',
            'mcp_arena.mcp',
            'mcp_arena.mcp.server',
            'mcp_arena.agent',
            'mcp_arena.agent.react',
            'mcp_arena.agent.reflection',
            'mcp_arena.agent.planning',
            'mcp_arena.agent.router',
            'mcp_arena.presents',
            'mcp_arena.tools',
            'mcp_arena.cli'
        ]
        
        for module in expected_modules:
            try:
                importlib.import_module(module)
            except ImportError as e:
                pytest.fail(f"Failed to import {module}: {e}")

    def test_no_circular_imports(self):
        """Test there are no circular imports."""
        # This is a basic test - more comprehensive testing would require
        # more sophisticated analysis
        modules_to_test = [
            'mcp_arena',
            'mcp_arena.mcp.server',
            'mcp_arena.agent.react',
            'mcp_arena.presents.github',
            'mcp_arena.tools.base'
        ]
        
        for module in modules_to_test:
            try:
                # Import and reload to catch circular dependencies
                mod = importlib.import_module(module)
                importlib.reload(mod)
            except (ImportError, RuntimeError) as e:
                if "circular" in str(e).lower():
                    pytest.fail(f"Circular import detected in {module}: {e}")

    def test_package_consistency(self):
        """Test package consistency across different parts."""
        import mcp_arena
        
        # Check that version is consistent
        version = getattr(mcp_arena, '__version__', None)
        assert version is not None, "Package version not set"
        
        # Check that main components are accessible
        assert hasattr(mcp_arena, 'mcp'), "mcp module not accessible"
        assert hasattr(mcp_arena, 'agent'), "agent module not accessible"
        assert hasattr(mcp_arena, 'presents'), "presents module not accessible"

    def test_python_version_compatibility(self):
        """Test Python version compatibility."""
        import sys
        
        # Check minimum Python version
        python_version = sys.version_info
        assert python_version >= (3, 8), f"Python 3.8+ required, got {python_version}"
        
        # Check if we're running on a supported platform
        supported_platforms = ['linux', 'darwin', 'win32']
        current_platform = sys.platform
        assert current_platform in supported_platforms, f"Platform {current_platform} may not be fully supported"


class TestDocumentationInstallation:
    """Test documentation installation and accessibility."""

    def test_documentation_files_exist(self):
        """Test documentation files exist."""
        project_root = Path(__file__).parent.parent
        doc_files = [
            'README.md',
            'INSTALLATION.md',
            'MCP_SERVERS_GUIDE.md',
            'AGENT_GUIDE.md',
            'TOOLS_GUIDE.md',
            'QUICKSTART.md'
        ]
        
        for doc_file in doc_files:
            doc_path = project_root / doc_file
            if doc_path.exists():
                try:
                    content = doc_path.read_text(encoding='utf-8')
                    assert len(content) > 0, f"{doc_file} is empty"
                except Exception as e:
                    pytest.fail(f"Error reading {doc_file}: {e}")
            else:
                pytest.warn(f"Documentation file {doc_file} not found")

    def test_documentation_links_valid(self):
        """Test documentation links are valid."""
        project_root = Path(__file__).parent.parent
        readme_path = project_root / 'README.md'
        
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding='utf-8')
                
                # Check for links to documentation files
                doc_links = [
                    '[Installation Guide](INSTALLATION.md)',
                    '[MCP Servers Guide](MCP_SERVERS_GUIDE.md)',
                    '[Agent Guide](AGENT_GUIDE.md)',
                    '[Tools Guide](TOOLS_GUIDE.md)',
                    '[Quick Start](QUICKSTART.md)'
                ]
                
                for link in doc_links:
                    assert link in content, f"Documentation link {link} not found in README.md"
                    
            except Exception as e:
                pytest.fail(f"Error checking README.md links: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
