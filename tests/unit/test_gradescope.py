import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import re
import uuid

# Add module path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../anonymization_scripts/gradescope')))
import gradescope_api  # type: ignore


def test_anti_cache_headers():
    """Test the generation of anti-cache headers"""
    headers = gradescope_api.anti_cache_headers()
    
    # Check required header fields
    assert 'User-Agent' in headers
    assert 'Cache-Control' in headers
    assert 'Pragma' in headers
    assert 'Expires' in headers
    assert 'X-Request-ID' in headers
    
    # Verify header values
    assert headers['Cache-Control'] == 'no-cache, no-store, must-revalidate, max-age=0'
    assert headers['Pragma'] == 'no-cache'
    assert headers['Expires'] == '0'
    
    # Verify request ID is in valid UUID format
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    assert uuid_pattern.match(headers['X-Request-ID'])
    
    # Verify each call generates a different request ID
    headers2 = gradescope_api.anti_cache_headers()
    assert headers['X-Request-ID'] != headers2['X-Request-ID']


@patch('requests.Session')
def test_login_successful(mock_session):
    """Test successful login"""
    # Configure mock objects
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    
    # Mock login page response
    mock_login_page = MagicMock()
    mock_login_page.text = '''
    <html>
        <body>
            <form>
                <input name="authenticity_token" value="fake-csrf-token">
            </form>
        </body>
    </html>
    '''
    mock_session_instance.get.return_value = mock_login_page
    
    # Mock response after login
    mock_login_resp = MagicMock()
    mock_login_resp.text = '<a href="/logout">Log Out</a>'
    mock_session_instance.post.return_value = mock_login_resp
    
    # Run test
    result = gradescope_api.login_to_gradescope('test@example.com', 'password123')
    
    # Verify results
    assert result == mock_session_instance
    
    # Verify calls
    mock_session_instance.get.assert_called_once_with('https://www.gradescope.com/login')
    mock_session_instance.post.assert_called_once()
    
    # Verify sent data
    call_args = mock_session_instance.post.call_args
    assert call_args[0][0] == 'https://www.gradescope.com/login'
    assert 'data' in call_args[1]
    
    post_data = call_args[1]['data']
    assert post_data['utf8'] == '✓'
    assert post_data['authenticity_token'] == 'fake-csrf-token'
    assert post_data['session[email]'] == 'test@example.com'
    assert post_data['session[password]'] == 'password123'
    assert post_data['commit'] == 'Log In'


@patch('requests.Session')
def test_login_failed(mock_session):
    """Test login failure"""
    # Configure mock objects
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    
    # Mock login page response
    mock_login_page = MagicMock()
    mock_login_page.text = '''
    <html>
        <body>
            <form>
                <input name="authenticity_token" value="fake-csrf-token">
            </form>
        </body>
    </html>
    '''
    mock_session_instance.get.return_value = mock_login_page
    
    # Mock failed login response (no Log Out link)
    mock_login_resp = MagicMock()
    mock_login_resp.text = '<div>Invalid email or password.</div>'
    mock_session_instance.post.return_value = mock_login_resp
    
    # Run test and verify exception
    with pytest.raises(Exception) as excinfo:
        gradescope_api.login_to_gradescope('wrong@example.com', 'wrong_password')
    
    assert "Login failed" in str(excinfo.value)


@patch('requests.Session')
def test_csrf_token_not_found(mock_session):
    """Test scenario when CSRF token is not found"""
    # Configure mock objects
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    
    # Mock login page without CSRF token
    mock_login_page = MagicMock()
    mock_login_page.text = '<html><body><form></form></body></html>'
    mock_session_instance.get.return_value = mock_login_page
    
    # Run test and verify exception (should fail due to missing CSRF token)
    with pytest.raises(TypeError):
        gradescope_api.login_to_gradescope('test@example.com', 'password123')


# Add additional tests to improve coverage
def test_anti_cache_headers_uniqueness():
    """Test uniqueness of multiple calls to anti-cache header generation"""
    # Generate multiple headers and check uniqueness
    headers_list = [gradescope_api.anti_cache_headers() for _ in range(5)]
    request_ids = [h['X-Request-ID'] for h in headers_list]
    
    # Check all IDs are unique
    assert len(request_ids) == len(set(request_ids))
    
    # Check all IDs have valid format
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    for req_id in request_ids:
        assert uuid_pattern.match(req_id)


@patch('requests.Session')
def test_login_malformed_response(mock_session):
    """Test handling of malformed responses"""
    # Configure mock objects
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    
    # Mock login page response
    mock_login_page = MagicMock()
    mock_login_page.text = '''
    <html>
        <body>
            <form>
                <input name="authenticity_token" value="fake-csrf-token">
            </form>
        </body>
    </html>
    '''
    mock_session_instance.get.return_value = mock_login_page
    
    # Mock malformed response
    mock_login_resp = MagicMock()
    mock_login_resp.text = '<html><body>Malformed response</body></html>'
    mock_session_instance.post.return_value = mock_login_resp
    
    # Run test and verify exception
    with pytest.raises(Exception) as excinfo:
        gradescope_api.login_to_gradescope('test@example.com', 'password123')
    
    assert "Login failed" in str(excinfo.value)