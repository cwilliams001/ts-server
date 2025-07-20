import pytest
import base64
import requests
import time
import sys
import os

# Add the parent directory to the path so we can import ts-server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module - handle the hyphen in filename
import importlib.util
spec = importlib.util.spec_from_file_location("ts_server", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ts-server.py"))
ts_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts_server)

class TestAuthentication:
    """Test authentication functionality."""
    
    def test_generate_password(self):
        """Test password generation."""
        password = ts_server.generate_password()
        assert len(password) == 12
        assert password.isalnum()
        
        # Test custom length
        password = ts_server.generate_password(20)
        assert len(password) == 20
    
    def test_auth_header_parsing_valid(self, test_server):
        """Test valid authentication header parsing."""
        server = test_server(use_auth=True, password="test123")
        handler = server.RequestHandlerClass(None, None, None, use_auth=True, password="test123")
        
        # Create valid auth header
        credentials = base64.b64encode(b"user:test123").decode('ascii')
        auth_header = f"Basic {credentials}"
        
        assert handler.authenticate(auth_header) == True
    
    def test_auth_header_parsing_invalid_password(self, test_server):
        """Test invalid password."""
        server = test_server(use_auth=True, password="test123")
        handler = server.RequestHandlerClass(None, None, None, use_auth=True, password="test123")
        
        # Create invalid auth header
        credentials = base64.b64encode(b"user:wrong").decode('ascii')
        auth_header = f"Basic {credentials}"
        
        assert handler.authenticate(auth_header) == False
    
    def test_auth_header_parsing_invalid_username(self, test_server):
        """Test invalid username."""
        server = test_server(use_auth=True, password="test123")
        handler = server.RequestHandlerClass(None, None, None, use_auth=True, password="test123")
        
        # Create invalid auth header
        credentials = base64.b64encode(b"admin:test123").decode('ascii')
        auth_header = f"Basic {credentials}"
        
        assert handler.authenticate(auth_header) == False
    
    def test_auth_header_malformed(self, test_server):
        """Test malformed authentication header."""
        server = test_server(use_auth=True, password="test123")
        handler = server.RequestHandlerClass(None, None, None, use_auth=True, password="test123")
        
        # Test various malformed headers
        assert handler.authenticate("Invalid") == False
        assert handler.authenticate("Basic") == False
        assert handler.authenticate("Basic invalidbase64!") == False
        assert handler.authenticate("Basic " + base64.b64encode(b"no-colon").decode()) == False
    
    def test_auth_timing_attack_resistance(self, test_server):
        """Test that authentication timing doesn't leak information."""
        server = test_server(use_auth=True, password="test123")
        handler = server.RequestHandlerClass(None, None, None, use_auth=True, password="test123")
        
        # Test with correct username, wrong password
        credentials1 = base64.b64encode(b"user:wrong").decode('ascii')
        auth_header1 = f"Basic {credentials1}"
        
        # Test with wrong username, wrong password
        credentials2 = base64.b64encode(b"wrong:wrong").decode('ascii')
        auth_header2 = f"Basic {credentials2}"
        
        # Both should return False without significant timing difference
        start1 = time.time()
        result1 = handler.authenticate(auth_header1)
        time1 = time.time() - start1
        
        start2 = time.time()
        result2 = handler.authenticate(auth_header2)
        time2 = time.time() - start2
        
        assert result1 == False
        assert result2 == False
        # Timing difference should be minimal (within 10ms)
        assert abs(time1 - time2) < 0.01