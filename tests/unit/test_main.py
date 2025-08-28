import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import main
import importlib
import importlib

# Add the parent directory to the path to import main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../anonymization_scripts'))



class TestMain:
    
    @patch('main.platform.system')
    @patch('main.gui')
    @patch('main.m')
    def test_main_success_flow(self, mock_m, mock_gui, mock_platform):
        """Test successful execution of main function"""
        # Setup mocks
        mock_platform.return_value = "Windows"
        mock_gui.gui_input.return_value = "test@email.com"
        mock_gui.gui_password_input.return_value = "password123"
        mock_session = MagicMock()
        mock_m.login.return_value = mock_session
        mock_m.get_hidden_data_path.return_value = "/test/path"
        mock_m.choose_courses.return_value = {"123": "Course 1", "456": "Course 2"}
        
        # Execute
        main.main()
        
        # Verify calls
        mock_m.login.assert_called_once_with("test@email.com", "password123")
        mock_m.get_hidden_data_path.assert_called_once()
        mock_m.choose_courses.assert_called_once()
        mock_m.anonymize_course.assert_called_once_with(
            mock_session, {"123": "Course 1", "456": "Course 2"}, 
            "/test/path/gradescope_roster", "/test/path"
        )
        mock_m.cleanup_folder.assert_called_once()
        mock_gui.gui_show_selection.assert_called_once()

    @patch('main.platform.system')
    @patch('main.gui')
    @patch('main.m')
    def test_main_no_courses_selected_twice(self, mock_m, mock_gui, mock_platform):
        """Test when no courses are selected twice, program exits"""
        # Setup mocks
        mock_platform.return_value = "Windows"
        mock_gui.gui_input.return_value = "test@email.com"
        mock_gui.gui_password_input.return_value = "password123"
        mock_session = MagicMock()
        mock_m.login.return_value = mock_session
        mock_m.get_hidden_data_path.return_value = "/test/path"
        mock_m.choose_courses.return_value = {}  # Empty dict both times
        
        # Execute
        main.main()
        
        # Verify
        assert mock_m.choose_courses.call_count == 2
        mock_m.anonymize_course.assert_not_called()
        mock_m.cleanup_folder.assert_not_called()

    @patch('main.platform.system')
    @patch('main.gui')
    @patch('main.m')
    def test_main_no_courses_first_time_success_second(self, mock_m, mock_gui, mock_platform):
        """Test when no courses selected first time but success second time"""
        # Setup mocks
        mock_platform.return_value = "Windows"
        mock_gui.gui_input.return_value = "test@email.com"
        mock_gui.gui_password_input.return_value = "password123"
        mock_session = MagicMock()
        mock_m.login.return_value = mock_session
        mock_m.get_hidden_data_path.return_value = "/test/path"
        mock_m.choose_courses.side_effect = [{}, {"123": "Course 1"}]  # Empty first, success second
        
        # Execute
        main.main()
        
        # Verify
        assert mock_m.choose_courses.call_count == 2
        mock_m.anonymize_course.assert_called_once()
        mock_m.cleanup_folder.assert_called_once()

    @patch('main.platform.system')
    def test_windows_gui_import(self, mock_platform):
        """Test that Windows platform imports gui_win"""
        mock_platform.return_value = "Windows"
        
        with patch.dict('sys.modules', {'gui_win': MagicMock(), 'gui_macOS': MagicMock()}):
            importlib.reload(main)
            # If we reach here without import error, test passes

    @patch('main.platform.system')
    def test_macos_gui_import(self, mock_platform):
        """Test that non-Windows platform imports gui_macOS"""
        mock_platform.return_value = "Darwin"
        
        with patch.dict('sys.modules', {'gui_win': MagicMock(), 'gui_macOS': MagicMock()}):
            importlib.reload(main)
            # If we reach here without import error, test passes

    @patch('main.platform.system')
    @patch('main.gui')
    @patch('main.m')
    @patch('builtins.print')
    def test_main_prints_welcome_message(self, mock_print, mock_m, mock_gui, mock_platform):
        """Test that welcome message is printed"""
        # Setup mocks
        mock_platform.return_value = "Windows"
        mock_gui.gui_input.return_value = "test@email.com"
        mock_gui.gui_password_input.return_value = "password123"
        mock_session = MagicMock()
        mock_m.login.return_value = mock_session
        mock_m.get_hidden_data_path.return_value = "/test/path"
        mock_m.choose_courses.return_value = {"123": "Course 1"}
        
        # Execute
        main.main()
        
        # Verify welcome message is printed
        mock_print.assert_any_call("Welcome to Gradescope Anonymizer")