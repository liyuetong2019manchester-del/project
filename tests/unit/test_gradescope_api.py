import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup
import json
import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../anonymization_scripts/gradescope')))
from gradescope_api import (
    anti_cache_headers,
    login_to_gradescope,
    get_assignment_id,
    get_course_id,
    check_id,
    input_correct_id
)


class TestAntiCacheHeaders:
    def test_returns_dict_with_required_keys(self):
        headers = anti_cache_headers()
        assert isinstance(headers, dict)
        assert 'User-Agent' in headers
        assert 'Cache-Control' in headers
        assert 'Pragma' in headers
        assert 'Expires' in headers
        assert 'X-Request-ID' in headers

    def test_cache_control_values(self):
        headers = anti_cache_headers()
        assert headers['Cache-Control'] == 'no-cache, no-store, must-revalidate, max-age=0'
        assert headers['Pragma'] == 'no-cache'
        assert headers['Expires'] == '0'

    def test_user_agent_is_valid(self):
        headers = anti_cache_headers()
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        ]
        assert headers['User-Agent'] in user_agents

    def test_request_id_is_uuid(self):
        headers = anti_cache_headers()
        # Should be able to parse as UUID
        uuid.UUID(headers['X-Request-ID'])


class TestGetAssignmentId:
    @patch('gradescope_api.BeautifulSoup')
    def test_successful_assignment_extraction(self, mock_soup):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = '<html></html>'
        mock_session.get.return_value = mock_response
        
        mock_assignment_table = Mock()
        mock_assignment_table.get.return_value = '{"table_data": [{"title": "Assignment 1", "id": "assignment_123"}, {"title": "Assignment 2", "id": "assignment_456"}]}'
        
        mock_soup_instance = Mock()
        mock_soup_instance.find.return_value = mock_assignment_table
        mock_soup.return_value = mock_soup_instance
        
        result = get_assignment_id(mock_session, '123')
        
        assert result == {'Assignment 1': '123', 'Assignment 2': '456'}

    @patch('gradescope_api.BeautifulSoup')
    def test_no_assignment_table_found(self, mock_soup):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = '<html></html>'
        mock_session.get.return_value = mock_response
        
        mock_soup_instance = Mock()
        mock_soup_instance.find.return_value = None
        mock_soup.return_value = mock_soup_instance
        
        result = get_assignment_id(mock_session, '123')
        
        assert result == {}

    @patch('gradescope_api.BeautifulSoup')
    def test_invalid_json_data(self, mock_soup):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = '<html></html>'
        mock_session.get.return_value = mock_response
        
        mock_assignment_table = Mock()
        mock_assignment_table.get.return_value = 'invalid json'
        
        mock_soup_instance = Mock()
        mock_soup_instance.find.return_value = mock_assignment_table
        mock_soup.return_value = mock_soup_instance
        
        result = get_assignment_id(mock_session, '123')
        
        assert result == {}


class TestGetCourseId:
    @patch('gradescope_api.BeautifulSoup')
    def test_successful_course_extraction(self, mock_soup):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = '<html></html>'
        mock_session.get.return_value = mock_response
        
        # Mock course structure
        mock_course_box = Mock()
        mock_course_box.get.return_value = '/courses/123'
        mock_shortname = Mock()
        mock_shortname.text = 'CS101'
        mock_course_box.find.return_value = mock_shortname
        
        mock_courses_for_term = Mock()
        mock_courses_for_term.find_all.return_value = [mock_course_box]
        
        mock_term = Mock()
        mock_term.text = 'Spring 2024'
        mock_term.find_next_sibling.return_value = mock_courses_for_term
        
        mock_course_list = Mock()
        mock_course_list.find_all.return_value = [mock_term]
        
        mock_instructor_heading = Mock()
        mock_instructor_heading.find_next.return_value = mock_course_list
        
        mock_soup_instance = Mock()
        mock_soup_instance.find.return_value = mock_instructor_heading
        mock_soup.return_value = mock_soup_instance
        
        result = get_course_id(mock_session)
        
        assert result == {'Spring 2024 - CS101': '123'}

    @patch('gradescope_api.BeautifulSoup')
    def test_no_instructor_heading_found(self, mock_soup):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = '<html></html>'
        mock_session.get.return_value = mock_response
        
        mock_soup_instance = Mock()
        mock_soup_instance.find.return_value = None
        mock_soup.return_value = mock_soup_instance
        
        with patch('builtins.print'):
            result = get_course_id(mock_session)
        
        assert result == {}


class TestCheckId:
    def test_valid_course_id(self):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Valid page content'
        mock_session.get.return_value = mock_response
        
        result = check_id(mock_session, '123')
        
        assert result is True

    def test_404_error(self):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        
        with patch('builtins.print'):
            result = check_id(mock_session, '123')
        
        assert result is False

    def test_unauthorized_access(self):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'You are not authorized to access this page'
        mock_session.get.return_value = mock_response
        
        with patch('builtins.print'):
            result = check_id(mock_session, '123')
        
        assert result is False

    def test_valid_assignment_id(self):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'Valid assignment page'
        mock_session.get.return_value = mock_response
        
        result = check_id(mock_session, '123', '456')
        
        assert result is True


class TestInputCorrectId:
    @patch('gradescope_api.check_id')
    def test_valid_course_id_first_try(self, mock_check_id):
        mock_session = Mock()
        mock_check_id.return_value = True
        
        result = input_correct_id(mock_session, '123')
        
        assert result == '123'

    @patch('gradescope_api.check_id')
    @patch('builtins.input')
    def test_invalid_then_valid_course_id(self, mock_input, mock_check_id):
        mock_session = Mock()
        mock_check_id.side_effect = [False, True]
        mock_input.return_value = '456'
        
        result = input_correct_id(mock_session, '123')
        
        assert result == '456'

    @patch('gradescope_api.check_id')
    @patch('builtins.input')
    def test_user_quits_course_id(self, mock_input, mock_check_id):
        mock_session = Mock()
        mock_check_id.return_value = False
        mock_input.return_value = 'q'
        
        result = input_correct_id(mock_session, '123')
        
        assert result is None

    @patch('gradescope_api.check_id')
    def test_valid_assignment_id_first_try(self, mock_check_id):
        mock_session = Mock()
        mock_check_id.return_value = True
        
        result = input_correct_id(mock_session, '123', '456')
        
        assert result == '456'

    @patch('gradescope_api.check_id')
    @patch('builtins.input')
    def test_user_quits_assignment_id(self, mock_input, mock_check_id):
        mock_session = Mock()
        mock_check_id.return_value = False
        mock_input.return_value = 'q'
        
        result = input_correct_id(mock_session, '123', '456')
        
        assert result is None