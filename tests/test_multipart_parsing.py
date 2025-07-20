import pytest
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

class TestMultipartParsing:
    """Test the multipart form data parsing without cgi."""
    
    def test_parse_multipart_form_data_single_file(self):
        """Test parsing a single file upload."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        test_data = b"""------WebKitFormBoundary7MA4YWxkTrZu0gW\r
Content-Disposition: form-data; name="file"; filename="test.txt"\r
Content-Type: text/plain\r
\r
Hello, World!\r
------WebKitFormBoundary7MA4YWxkTrZu0gW--\r
"""
        
        files = ts_server.parse_multipart_form_data(test_data, boundary)
        
        assert len(files) == 1
        assert files[0]['filename'] == 'test.txt'
        assert files[0]['content'] == b'Hello, World!'
    
    def test_parse_multipart_form_data_multiple_files(self):
        """Test parsing multiple file uploads."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        test_data = b"""------WebKitFormBoundary7MA4YWxkTrZu0gW\r
Content-Disposition: form-data; name="file1"; filename="test1.txt"\r
Content-Type: text/plain\r
\r
File 1 content\r
------WebKitFormBoundary7MA4YWxkTrZu0gW\r
Content-Disposition: form-data; name="file2"; filename="test2.txt"\r
Content-Type: text/plain\r
\r
File 2 content\r
------WebKitFormBoundary7MA4YWxkTrZu0gW--\r
"""
        
        files = ts_server.parse_multipart_form_data(test_data, boundary)
        
        assert len(files) == 2
        assert files[0]['filename'] == 'test1.txt'
        assert files[0]['content'] == b'File 1 content'
        assert files[1]['filename'] == 'test2.txt'
        assert files[1]['content'] == b'File 2 content'
    
    def test_parse_multipart_form_data_no_files(self):
        """Test parsing form data with no files."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        test_data = b"""------WebKitFormBoundary7MA4YWxkTrZu0gW\r
Content-Disposition: form-data; name="field"\r
\r
value\r
------WebKitFormBoundary7MA4YWxkTrZu0gW--\r
"""
        
        files = ts_server.parse_multipart_form_data(test_data, boundary)
        
        assert len(files) == 0
    
    def test_parse_multipart_form_data_empty_filename(self):
        """Test parsing form data with empty filename."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        test_data = b"""------WebKitFormBoundary7MA4YWxkTrZu0gW\r
Content-Disposition: form-data; name="file"; filename=""\r
Content-Type: text/plain\r
\r
Empty filename content\r
------WebKitFormBoundary7MA4YWxkTrZu0gW--\r
"""
        
        files = ts_server.parse_multipart_form_data(test_data, boundary)
        
        # Should ignore files with empty filenames
        assert len(files) == 0
    
    def test_parse_multipart_form_data_malformed(self):
        """Test parsing malformed multipart data."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        test_data = b"""malformed data without proper boundaries"""
        
        files = ts_server.parse_multipart_form_data(test_data, boundary)
        
        assert len(files) == 0