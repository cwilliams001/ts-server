import pytest
import tempfile
import os
import shutil
import threading
import time
from http.server import ThreadingHTTPServer
from functools import partial
import sys

# Add the parent directory to the path so we can import ts-server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module - handle the hyphen in filename
import importlib.util
spec = importlib.util.spec_from_file_location("ts_server", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ts-server.py"))
ts_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts_server)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    os.chdir(temp_dir)
    yield temp_dir
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_server():
    """Create a test server instance."""
    def _create_server(port=0, use_auth=False, password="test123"):
        handler = partial(ts_server.AuthHandler, use_auth=use_auth, password=password)
        server = ThreadingHTTPServer(('localhost', port), handler)
        return server
    return _create_server

@pytest.fixture
def running_server(test_server, temp_dir):
    """Create and start a test server in a background thread."""
    server = test_server()
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    # Give the server time to start
    time.sleep(0.1)
    
    yield server
    
    server.shutdown()
    server.server_close()