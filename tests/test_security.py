import pytest
import os
import tempfile
import sys

# Add the parent directory to the path so we can import ts-server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module - handle the hyphen in filename
import importlib.util
spec = importlib.util.spec_from_file_location("ts_server", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ts-server.py"))
ts_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts_server)

class TestSecurity:
    """Test security features and protections."""
    
    def test_filename_sanitization_basic(self, test_server):
        """Test basic filename sanitization."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Test normal filename
        assert handler.sanitize_filename("test.txt") == "test.txt"
        
        # Test filename with extension
        assert handler.sanitize_filename("document.pdf") == "document.pdf"
    
    def test_filename_sanitization_path_traversal(self, test_server):
        """Test path traversal attack prevention."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Test directory traversal attempts
        assert handler.sanitize_filename("../../../etc/passwd") == "passwd"
        assert handler.sanitize_filename("..\\..\\windows\\system32\\config") == "config"
        assert handler.sanitize_filename("/etc/passwd") == "passwd"
        assert handler.sanitize_filename("\\windows\\system32\\config") == "config"
        
        # Test relative path components
        assert handler.sanitize_filename("./file.txt") == "file.txt"
        assert handler.sanitize_filename(".\\file.txt") == "file.txt"
    
    def test_filename_sanitization_dangerous_chars(self, test_server):
        """Test removal of dangerous characters."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Test dangerous characters are replaced with underscores
        dangerous_chars = '<>:"/\\|?*'
        for char in dangerous_chars:
            result = handler.sanitize_filename(f"test{char}file.txt")
            assert char not in result
            assert "_" in result
    
    def test_filename_sanitization_hidden_files(self, test_server):
        """Test handling of hidden files."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Test hidden files get prefixed
        assert handler.sanitize_filename(".hidden") == "file_.hidden"
        assert handler.sanitize_filename(".bashrc") == "file_.bashrc"
    
    def test_filename_sanitization_reserved_names(self, test_server):
        """Test handling of reserved Windows filenames."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'lpt1']
        for name in reserved_names:
            result = handler.sanitize_filename(name)
            assert result.startswith("file_")
            
            # Test case insensitive
            result = handler.sanitize_filename(name.upper())
            assert result.startswith("file_")
    
    def test_filename_sanitization_empty_names(self, test_server):
        """Test handling of empty or invalid filenames."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Test empty filename
        with pytest.raises(ValueError):
            handler.sanitize_filename("")
        
        # Test None filename
        with pytest.raises(ValueError):
            handler.sanitize_filename(None)
        
        # Test filenames that become empty after sanitization
        result = handler.sanitize_filename(".")
        assert result.startswith("uploaded_file_")
        
        result = handler.sanitize_filename("..")
        assert result.startswith("uploaded_file_")
    
    def test_filename_sanitization_unicode(self, test_server):
        """Test handling of unicode filenames."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Test unicode characters are preserved
        assert handler.sanitize_filename("测试文件.txt") == "测试文件.txt"
        assert handler.sanitize_filename("café.pdf") == "café.pdf"
        assert handler.sanitize_filename("файл.doc") == "файл.doc"
    
    def test_list_directory_json_security(self, test_server, temp_dir):
        """Test that directory listing doesn't expose hidden files."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        handler.directory = temp_dir
        
        # Create test files including hidden ones
        with open(os.path.join(temp_dir, "visible.txt"), "w") as f:
            f.write("test")
        with open(os.path.join(temp_dir, ".hidden"), "w") as f:
            f.write("secret")
        
        files = handler.list_directory_json()
        filenames = [f['name'] for f in files]
        
        assert "visible.txt" in filenames
        assert ".hidden" not in filenames
    
    def test_error_message_sanitization(self, test_server):
        """Test that error messages don't leak sensitive information."""
        server = test_server()
        handler = server.RequestHandlerClass(None, None, None)
        
        # Test that authenticate method doesn't log sensitive details
        import logging
        import io
        
        log_capture = io.StringIO()
        log_handler = logging.StreamHandler(log_capture)
        logging.getLogger().addHandler(log_handler)
        
        # Trigger authentication error
        handler.authenticate("invalid header")
        
        log_output = log_capture.getvalue()
        assert "Failed to parse authentication header" in log_output
        # Should not contain the actual invalid header content
        assert "invalid header" not in log_output
        
        logging.getLogger().removeHandler(log_handler)