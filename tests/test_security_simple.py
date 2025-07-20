import pytest
import os
import tempfile
import sys
import io
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import ts-server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module - handle the hyphen in filename
import importlib.util
spec = importlib.util.spec_from_file_location("ts_server", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ts-server.py"))
ts_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts_server)

class TestSecuritySimple:
    """Test security features with simplified setup."""
    
    def create_mock_handler(self, use_auth=False, password="test123"):
        """Create a mock handler for testing."""
        # Create a mock handler that doesn't require socket setup
        handler = Mock()
        handler.use_auth = use_auth
        handler.username = 'user'
        handler.password = password
        handler.directory = '.'
        
        # Bind the actual methods we want to test
        handler.authenticate = ts_server.AuthHandler.authenticate.__get__(handler)
        handler.sanitize_filename = ts_server.AuthHandler.sanitize_filename.__get__(handler)
        handler.list_directory_json = ts_server.AuthHandler.list_directory_json.__get__(handler)
        handler.add_security_headers = ts_server.AuthHandler.add_security_headers.__get__(handler)
        
        return handler
    
    def test_filename_sanitization_basic(self):
        """Test basic filename sanitization."""
        handler = self.create_mock_handler()
        
        # Test normal filename
        assert handler.sanitize_filename("test.txt") == "test.txt"
        assert handler.sanitize_filename("document.pdf") == "document.pdf"
    
    def test_filename_sanitization_path_traversal(self):
        """Test path traversal attack prevention."""
        handler = self.create_mock_handler()
        
        # Test directory traversal attempts
        assert handler.sanitize_filename("../../../etc/passwd") == "passwd"
        # On Linux, backslash paths get sanitized but .. becomes hidden file
        result = handler.sanitize_filename("..\\..\\windows\\system32\\config") 
        assert result.startswith("file_")  # Should be prefixed due to starting with ..
        assert handler.sanitize_filename("/etc/passwd") == "passwd"
        assert handler.sanitize_filename("\\windows\\system32\\config") == "_windows_system32_config"
        
        # Test relative path components
        assert handler.sanitize_filename("./file.txt") == "file.txt"
        assert handler.sanitize_filename(".\\file.txt") == "file_._file.txt"  # Backslash becomes underscore
    
    def test_filename_sanitization_dangerous_chars(self):
        """Test removal of dangerous characters."""
        handler = self.create_mock_handler()
        
        # Test dangerous characters that don't get removed by basename
        dangerous_chars = '<>:|?*'  # Removed / and \ as they get handled by basename
        for char in dangerous_chars:
            result = handler.sanitize_filename(f"test{char}file.txt")
            assert char not in result
            assert "_" in result
            
        # Test path separators are handled by basename (better security)
        assert handler.sanitize_filename("test/file.txt") == "file.txt"
        # On Linux, backslash is not a path separator, so it gets replaced with underscore
        assert handler.sanitize_filename("test\\file.txt") == "test_file.txt"
    
    def test_filename_sanitization_hidden_files(self):
        """Test handling of hidden files."""
        handler = self.create_mock_handler()
        
        # Test hidden files get prefixed
        assert handler.sanitize_filename(".hidden") == "file_.hidden"
        assert handler.sanitize_filename(".bashrc") == "file_.bashrc"
    
    def test_filename_sanitization_reserved_names(self):
        """Test handling of reserved Windows filenames."""
        handler = self.create_mock_handler()
        
        reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'lpt1']
        for name in reserved_names:
            result = handler.sanitize_filename(name)
            assert result.startswith("file_")
            
            # Test case insensitive
            result = handler.sanitize_filename(name.upper())
            assert result.startswith("file_")
    
    def test_filename_sanitization_empty_names(self):
        """Test handling of empty or invalid filenames."""
        handler = self.create_mock_handler()
        
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
    
    def test_authentication_valid(self):
        """Test valid authentication."""
        import base64
        
        handler = self.create_mock_handler(use_auth=True, password="test123")
        
        # Create valid auth header
        credentials = base64.b64encode(b"user:test123").decode('ascii')
        auth_header = f"Basic {credentials}"
        
        assert handler.authenticate(auth_header) == True
    
    def test_authentication_invalid(self):
        """Test invalid authentication."""
        import base64
        
        handler = self.create_mock_handler(use_auth=True, password="test123")
        
        # Test invalid password
        credentials = base64.b64encode(b"user:wrong").decode('ascii')
        auth_header = f"Basic {credentials}"
        assert handler.authenticate(auth_header) == False
        
        # Test invalid username
        credentials = base64.b64encode(b"admin:test123").decode('ascii')
        auth_header = f"Basic {credentials}"
        assert handler.authenticate(auth_header) == False
    
    def test_authentication_malformed(self):
        """Test malformed authentication headers."""
        import base64
        
        handler = self.create_mock_handler(use_auth=True, password="test123")
        
        # Test various malformed headers
        assert handler.authenticate("Invalid") == False
        assert handler.authenticate("Basic") == False
        assert handler.authenticate("Basic invalidbase64!") == False
        assert handler.authenticate("Basic " + base64.b64encode(b"no-colon").decode()) == False
    
    def test_list_directory_json_with_temp_dir(self):
        """Test directory listing with a temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = self.create_mock_handler()
            handler.directory = temp_dir
            
            # Test empty directory
            files = handler.list_directory_json()
            assert files == []
            
            # Create test files
            test_content = "test content"
            with open(os.path.join(temp_dir, "test1.txt"), "w") as f:
                f.write(test_content)
            with open(os.path.join(temp_dir, "test2.pdf"), "w") as f:
                f.write(test_content)
            with open(os.path.join(temp_dir, ".hidden"), "w") as f:
                f.write("secret")
            
            files = handler.list_directory_json()
            filenames = [f['name'] for f in files]
            
            # Should include visible files but not hidden ones
            assert "test1.txt" in filenames
            assert "test2.pdf" in filenames
            assert ".hidden" not in filenames
            assert len([f for f in files if not f['name'].startswith('.')]) == 2
    
    def test_security_headers(self):
        """Test security headers are set correctly."""
        handler = self.create_mock_handler()
        
        # Mock the send_header method
        headers_sent = {}
        handler.send_header = lambda name, value: headers_sent.update({name: value})
        
        handler.add_security_headers()
        
        expected_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, expected_value in expected_headers.items():
            assert header in headers_sent
            assert headers_sent[header] == expected_value
    
    def test_password_generation(self):
        """Test password generation function."""
        password = ts_server.generate_password()
        assert len(password) == 12
        assert password.isalnum()
        
        # Test custom length
        password = ts_server.generate_password(20)
        assert len(password) == 20
        
        # Test uniqueness
        passwords = [ts_server.generate_password() for _ in range(100)]
        assert len(set(passwords)) == 100  # All passwords should be unique