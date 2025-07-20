import pytest
import os
import json
import tempfile
import io
import sys

# Add the parent directory to the path so we can import ts-server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module - handle the hyphen in filename
import importlib.util
spec = importlib.util.spec_from_file_location("ts_server", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ts-server.py"))
ts_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts_server)

class TestFunctionality:
    """Test core functionality of the file server."""
    
    def test_password_generation_uniqueness(self):
        """Test that generated passwords are unique."""
        passwords = [ts_server.generate_password() for _ in range(100)]
        assert len(set(passwords)) == 100  # All passwords should be unique
    
    def test_list_directory_json_empty(self, test_server, temp_dir):
        """Test JSON directory listing with empty directory."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        handler.directory = temp_dir
        
        files = handler.list_directory_json()
        assert files == []
    
    def test_list_directory_json_with_files(self, test_server, temp_dir):
        """Test JSON directory listing with files."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        handler.directory = temp_dir
        
        # Create test files
        test_content = "test content"
        with open(os.path.join(temp_dir, "test1.txt"), "w") as f:
            f.write(test_content)
        with open(os.path.join(temp_dir, "test2.pdf"), "w") as f:
            f.write(test_content)
        
        files = handler.list_directory_json()
        assert len(files) == 2
        
        filenames = [f['name'] for f in files]
        assert "test1.txt" in filenames
        assert "test2.pdf" in filenames
        
        # Check file sizes
        for file_info in files:
            assert 'size' in file_info
            assert file_info['size'] == len(test_content)
    
    def test_list_directory_json_subdirectories_ignored(self, test_server, temp_dir):
        """Test that subdirectories are not included in file listing."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        handler.directory = temp_dir
        
        # Create test file and subdirectory
        with open(os.path.join(temp_dir, "test.txt"), "w") as f:
            f.write("test")
        os.mkdir(os.path.join(temp_dir, "subdir"))
        
        files = handler.list_directory_json()
        filenames = [f['name'] for f in files]
        
        assert "test.txt" in filenames
        assert "subdir" not in filenames
        assert len(files) == 1
    
    def test_list_directory_json_error_handling(self, test_server):
        """Test error handling in directory listing."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        handler.directory = "/nonexistent/directory"
        
        files = handler.list_directory_json()
        assert files == []
    
    def test_security_headers_presence(self, test_server):
        """Test that security headers are properly set."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Mock the send_header method to capture headers
        headers_sent = {}
        original_send_header = handler.send_header
        
        def mock_send_header(name, value):
            headers_sent[name] = value
            
        handler.send_header = mock_send_header
        handler.add_security_headers()
        
        # Check that all security headers are present
        expected_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, expected_value in expected_headers.items():
            assert header in headers_sent
            assert headers_sent[header] == expected_value
    
    def test_sanitize_filename_preserves_extension(self, test_server):
        """Test that file extensions are preserved during sanitization."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        test_cases = [
            ("document.pdf", "document.pdf"),
            ("image.jpg", "image.jpg"),
            ("archive.tar.gz", "archive.tar.gz"),
            ("script.py", "script.py"),
            ("data.json", "data.json")
        ]
        
        for input_name, expected in test_cases:
            result = handler.sanitize_filename(input_name)
            assert result == expected
    
    def test_sanitize_filename_long_names(self, test_server):
        """Test handling of very long filenames."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Create a very long filename
        long_name = "a" * 300 + ".txt"
        result = handler.sanitize_filename(long_name)
        
        # Should still be valid and end with .txt
        assert result.endswith(".txt")
        assert len(result) <= 255  # Most filesystems have 255 char limit
    
    def test_server_startup_config(self):
        """Test server configuration and startup parameters."""
        # Test that we can create handler with different configs
        handler_no_auth = ts_server.AuthHandler(None, None, None, use_auth=False, password='')
        assert handler_no_auth.use_auth == False
        assert handler_no_auth.password == ''
        
        handler_with_auth = ts_server.AuthHandler(None, None, None, use_auth=True, password='test123')
        assert handler_with_auth.use_auth == True
        assert handler_with_auth.password == 'test123'
        assert handler_with_auth.username == 'user'