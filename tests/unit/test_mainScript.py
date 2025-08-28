import pytest
import sys
import os
import platform
from unittest.mock import patch, MagicMock, mock_open
import shutil
import tempfile
import json

from anonymization_scripts.mainScript import check_uploaded_roster
from anonymization_scripts.mainScript import check_uploaded_roster
from anonymization_scripts.mainScript import check_uploaded_roster
from anonymization_scripts.mainScript import get_roster
from anonymization_scripts.mainScript import choose_courses
from anonymization_scripts.mainScript import choose_courses
from anonymization_scripts.mainScript import choose_courses
from anonymization_scripts.mainScript import choose_assignments
from anonymization_scripts.mainScript import choose_assignments
from anonymization_scripts.mainScript import anonymize_course
from anonymization_scripts.mainScript import anonymize_course
from anonymization_scripts.mainScript import get_hidden_data_path, TEMP_PATHS
from anonymization_scripts.mainScript import cleanup_folder
from anonymization_scripts.mainScript import cleanup_folder
from anonymization_scripts.mainScript import get_base_dirs
from anonymization_scripts.mainScript import get_decimal
from anonymization_scripts.mainScript import get_hidden_data_path
from anonymization_scripts.mainScript import anonymize_course
from anonymization_scripts.mainScript import get_program_dir
from anonymization_scripts.mainScript import get_program_dir
from anonymization_scripts.mainScript import get_output_path
from anonymization_scripts.mainScript import login

class TestMainScript:
    
    @patch('anonymization_scripts.mainScript.sys')
    @patch('anonymization_scripts.mainScript.os.path.dirname')
    @patch('anonymization_scripts.mainScript.os.path.abspath')
    def test_get_program_dir_frozen(self, mock_abspath, mock_dirname, mock_sys):
        mock_sys.frozen = True
        mock_sys.executable = '/path/to/executable'
        mock_dirname.return_value = '/path/to'
        
        result = get_program_dir()
        
        assert result == '/path/to'
        mock_dirname.assert_called_once_with('/path/to/executable')

    @patch('anonymization_scripts.mainScript.sys')
    @patch('anonymization_scripts.mainScript.os.path.dirname')
    @patch('anonymization_scripts.mainScript.os.path.abspath')
    def test_get_program_dir_not_frozen(self, mock_abspath, mock_dirname, mock_sys):
        mock_sys.frozen = False
        mock_abspath.return_value = '/path/to/file.py'
        mock_dirname.return_value = '/path/to'
        
        result = get_program_dir()
        
        assert result == '/path/to'

    @patch('anonymization_scripts.mainScript.get_program_dir')
    @patch('anonymization_scripts.mainScript.os.path.join')
    def test_get_output_path(self, mock_join, mock_get_program_dir):
        mock_get_program_dir.return_value = '/program/dir'
        mock_join.return_value = '/program/dir/test.txt'
        
        result = get_output_path('test.txt')
        
        assert result == '/program/dir/test.txt'
        mock_join.assert_called_once_with('/program/dir', 'test.txt')

    @patch('anonymization_scripts.mainScript.platform.system')
    @patch('anonymization_scripts.mainScript.time.strftime')
    @patch('anonymization_scripts.mainScript.os.getenv')
    @patch('anonymization_scripts.mainScript.Path')
    def test_get_hidden_data_path_windows(self, mock_path, mock_getenv, mock_strftime, mock_system):
        mock_system.return_value = "Windows"
        mock_strftime.return_value = "20230101_120000"
        mock_getenv.return_value = "/appdata"
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.__truediv__.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = "/appdata/anon_tool_20230101_120000"
        
        TEMP_PATHS.clear()
        result = get_hidden_data_path()
        
        assert result == "/appdata/anon_tool_20230101_120000"
        assert "/appdata/anon_tool_20230101_120000" in TEMP_PATHS
        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('builtins.input')
    def test_get_decimal_valid_input(self, mock_input):
        mock_input.return_value = "123"
        
        result = get_decimal("Enter number: ")
        
        assert result == 123

    @patch('builtins.input')
    def test_get_decimal_quit(self, mock_input):
        mock_input.side_effect = ["invalid", "q"]
        
        with pytest.raises(SystemExit):
            get_decimal("Enter number: ")

    @patch('anonymization_scripts.mainScript.api.login_to_gradescope')
    def test_login(self, mock_login):
        mock_session = MagicMock()
        mock_login.return_value = mock_session
        
        result = login("test@email.com", "password")
        
        assert result == mock_session
        mock_login.assert_called_once_with("test@email.com", "password")

    def test_get_base_dirs(self):
        
        result = get_base_dirs("/anon/path", "course123", "assign456")
        
        expected = {
            'zip': '/anon/path/gradescope_raw_zips_course123_assign456',
            'pdf': '/anon/path/gradescope_graded_copies_course123_assign456'
        }
        assert result == expected

    @patch('anonymization_scripts.mainScript.shutil.rmtree')
    @patch('anonymization_scripts.mainScript.os.path.exists')
    @patch('anonymization_scripts.mainScript.time.sleep')
    @patch('builtins.print')
    def test_cleanup_folder(self, mock_print, mock_sleep, mock_exists, mock_rmtree):
        mock_exists.return_value = True
        
        cleanup_folder(["/temp/path1", "/temp/path2"])
        
        assert mock_sleep.call_count == 2
        assert mock_exists.call_count == 2
        assert mock_rmtree.call_count == 2

    @patch('anonymization_scripts.mainScript.api.get_course_id')
    @patch('anonymization_scripts.mainScript.gui')
    def test_choose_courses_success(self, mock_gui, mock_get_course_id):
        mock_session = MagicMock()
        mock_get_course_id.return_value = {"Course 1": "course_id_1", "Course 2": "course_id_2"}
        mock_gui.gui_choose_from_list.return_value = ["Course 1"]
        mock_gui.gui_show_selection.return_value = True
        
        result = choose_courses(mock_session)
        
        expected = {"course_id_1": "Course 1"}
        assert result == expected

    @patch('anonymization_scripts.mainScript.api.get_assignment_id')
    @patch('anonymization_scripts.mainScript.gui')
    def test_choose_assignments_success(self, mock_gui, mock_get_assignment_id):
        mock_session = MagicMock()
        mock_get_assignment_id.return_value = {"Assignment 1": "assign_id_1"}
        mock_gui.gui_choose_from_list.return_value = ["Assignment 1"]
        mock_gui.gui_show_selection.return_value = True
        
        result = choose_assignments(mock_session, "course_id")
        
        expected = {"assign_id_1": "Assignment 1"}
        assert result == expected

    @patch('anonymization_scripts.mainScript.down.download_roster')
    @patch('anonymization_scripts.mainScript.roster.read_roster_file')
    @patch('anonymization_scripts.mainScript.gui')
    @patch('anonymization_scripts.mainScript.os.path.exists')
    @patch('anonymization_scripts.mainScript.os.remove')
    def test_check_uploaded_roster_success(self, mock_remove, mock_exists, mock_gui, mock_read_roster, mock_download):
        mock_session = MagicMock()
        mock_gui.gui_show_selection.return_value = True
        mock_read_roster.return_value = True
        mock_exists.return_value = True
        
        check_uploaded_roster(mock_session, "upload_course", "/roster/dir", "/new/roster/path")
        
        mock_download.assert_called_once()
        mock_remove.assert_called_once()

    @patch('anonymization_scripts.mainScript.down.download_roster')
    @patch('anonymization_scripts.mainScript.roster.read_roster_file')
    @patch('anonymization_scripts.mainScript.roster.create_anonymized_roster')
    @patch('anonymization_scripts.mainScript.core.create_anonymization_mapping')
    @patch('anonymization_scripts.mainScript.core.save_mapping_table')
    @patch('anonymization_scripts.mainScript.check_uploaded_roster')
    @patch('anonymization_scripts.mainScript.get_output_path')
    def test_get_roster(self, mock_get_output, mock_check_roster, mock_save_mapping, 
                       mock_create_mapping, mock_create_anon_roster, mock_read_roster, mock_download):
        mock_session = MagicMock()
        mock_read_roster.return_value = (["student1"], {"student1": "role1"})
        mock_create_mapping.return_value = {"student1": "anon1"}
        mock_get_output.return_value = "/output/roster.csv"
        
        result = get_roster(mock_session, "/roster/dir", ["course1"], "upload_course", "/anon/path")
        
        assert result == (["student1"], {"student1": "anon1"})
        mock_download.assert_called()
        mock_save_mapping.assert_called()
        mock_create_anon_roster.assert_called()
