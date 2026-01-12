import sys
import unittest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from mcp_arena.cli import app

runner = CliRunner()

class TestCLI(unittest.TestCase):
    
    @patch("mcp_arena.cli._get_available_presets")
    def test_list(self, mock_get_presets):
        mock_get_presets.return_value = {"github": "github", "test": "test"}
        result = runner.invoke(app, ["list"])
        # print(result.stdout) # Caused UnicodeEncodeError on Windows console
        self.assertEqual(result.exit_code, 0)
        self.assertIn("github", result.stdout)
        self.assertIn("test", result.stdout)

    @patch("mcp_arena.cli._load_server_class")
    @patch("mcp_arena.cli._get_available_presets")
    def test_run_mock_server(self, mock_get_presets, mock_load_class):
        mock_get_presets.return_value = {"mock": "mock"}
        
        # Mock class
        MockServer = MagicMock()
        MockServer.__name__ = "MockServer"
        mock_load_class.return_value = MockServer
        
        # Run command with extra args
        result = runner.invoke(app, ["run", "--mcp-server", "mock", "--token", "123", "--debug"])
        
        print(f"Exit code: {result.exit_code}")
        print(f"Mock calls: {MockServer.mock_calls}")
        try:
            print(f"Output: {result.stdout.encode('utf-8', errors='ignore')}")
        except:
            pass
            
        self.assertEqual(result.exit_code, 0)
        
        # Verify constructor called with correct args
        MockServer.assert_called_with(token="123", debug=True)
        # Verify run called
        MockServer.return_value.run.assert_called_once()

if __name__ == "__main__":
    unittest.main()
