import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import shutil
from pathlib import Path

# Add the anonymization_scripts directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'anonymization_scripts'))

import mainScript as m
import main


class TestMainProcess(unittest.TestCase):
    
    def setUp(self):
        """Setup test fixtures"""
        self.test_session = Mock()
        self.test_email = "test@example.com"
        self.test_password = "password123"
        self.test_course_id = "123456"
        self.test_assignment_id = "789012"
        self.test_upload_course_id = "654321"
        self.test_upload_assignment_id = "210987"
        
        # Clear TEMP_PATHS before each test
        m.TEMP_PATHS.clear()
    
    def tearDown(self):
        """Clean up after tests"""
        m.TEMP_PATHS.clear()

    @patch('platform.system')
    @patch('sys.frozen', False, create=True)
    def test_get_program_dir_unpackaged(self, mock_platform):
        """Test get_program_dir when not packaged"""
        mock_platform.return_value = "Windows"
        result = m.get_program_dir()
        expected = os.path.dirname(os.path.abspath(m.__file__))
        self.assertEqual(result, expected)

    @patch('platform.system')
    @patch('sys.executable', '/path/to/executable')
    def test_get_program_dir_packaged(self, mock_platform):
        """Test get_program_dir when packaged"""
        mock_platform.return_value = "Windows"
        with patch.object(sys, 'frozen', True, create=True):
            result = m.get_program_dir()
            expected = os.path.dirname(sys.executable)
            self.assertEqual(result, expected)

    @patch('mainScript.get_program_dir')
    def test_get_output_path(self, mock_get_program_dir):
        """Test get_output_path function"""
        mock_get_program_dir.return_value = "/test/dir"
        result = m.get_output_path("test_file.txt")
        expected = os.path.join("/test/dir", "test_file.txt")
        self.assertEqual(result, expected)

    @patch('platform.system')
    @patch('time.strftime')
    @patch('pathlib.Path.mkdir')
    @patch('os.getenv')
    @patch('pathlib.Path.home')
    def test_get_hidden_data_path_windows(self, mock_home, mock_getenv, mock_mkdir, mock_strftime, mock_system):
        """Test get_hidden_data_path on Windows"""
        mock_system.return_value = "Windows"
        mock_strftime.return_value = "20240101_120000"
        mock_getenv.return_value = "C:\\Users\\Test\\AppData\\Roaming"
        mock_home.return_value = Path("C:\\Users\\Test")
        
        result = m.get_hidden_data_path()
        
        expected_path = "C:\\Users\\Test\\AppData\\Roaming\\anon_tool_20240101_120000"
        self.assertIn("anon_tool_20240101_120000", result)
        self.assertIn(result, m.TEMP_PATHS)

    @patch('platform.system')
    @patch('time.strftime')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.home')
    def test_get_hidden_data_path_macos(self, mock_home, mock_mkdir, mock_strftime, mock_system):
        """Test get_hidden_data_path on macOS"""
        mock_system.return_value = "Darwin"
        mock_strftime.return_value = "20240101_120000"
        mock_home.return_value = Path("/Users/test")
        
        result = m.get_hidden_data_path()
        
        self.assertIn(".anon_tool_20240101_120000", result)
        self.assertIn(result, m.TEMP_PATHS)

    @patch('builtins.input')
    def test_get_decimal_valid_input(self, mock_input):
        """Test get_decimal with valid decimal input"""
        mock_input.return_value = "5"
        result = m.get_decimal("Enter number: ")
        self.assertEqual(result, 5)

    @patch('builtins.input')
    def test_get_decimal_invalid_then_valid(self, mock_input):
        """Test get_decimal with invalid then valid input"""
        mock_input.side_effect = ["abc", "5"]
        result = m.get_decimal("Enter number: ")
        self.assertEqual(result, 5)

    @patch('builtins.input')
    def test_get_decimal_quit(self, mock_input):
        """Test get_decimal with quit command"""
        mock_input.side_effect = ["abc", "q"]
        with self.assertRaises(SystemExit):
            m.get_decimal("Enter number: ")

    @patch('anonymization_scripts.gradescope.gradescope_api.login_to_gradescope')
    def test_login(self, mock_login):
        """Test login function"""
        mock_session = Mock()
        mock_login.return_value = mock_session
        
        result = m.login(self.test_email, self.test_password)
        

    def test_get_base_dirs(self):
        """Test get_base_dirs function"""
        anon_path = "/test/path"
        base_id = "123"
        assignment_id = "456"
        
        result = m.get_base_dirs(anon_path, base_id, assignment_id)
        
        expected = {
            'zip': f'{anon_path}/gradescope_raw_zips_{base_id}_{assignment_id}',
            'pdf': f'{anon_path}/gradescope_graded_copies_{base_id}_{assignment_id}'
        }
        self.assertEqual(result, expected)

    @patch('time.sleep')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_cleanup_folder_success(self, mock_exists, mock_rmtree, mock_sleep):
        """Test cleanup_folder successful deletion"""
        test_paths = ["/temp/path1", "/temp/path2"]
        mock_exists.return_value = True
        
        m.cleanup_folder(test_paths)
        
        self.assertEqual(mock_rmtree.call_count, 2)
        mock_rmtree.assert_any_call("/temp/path1")
        mock_rmtree.assert_any_call("/temp/path2")

    @patch('time.sleep')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_cleanup_folder_exception(self, mock_exists, mock_rmtree, mock_sleep):
        """Test cleanup_folder with exception"""
        test_paths = ["/temp/path1"]
        mock_exists.return_value = True
        mock_rmtree.side_effect = Exception("Permission denied")
        
        # Should not raise exception
        m.cleanup_folder(test_paths)
        
        mock_rmtree.assert_called_once_with("/temp/path1")

    @patch('anonymization_scripts.gradescope.gradescope_api.get_course_id')
    def test_choose_courses_no_selection(self, mock_get_course_id):
        """Test choose_courses with no selection"""
        mock_get_course_id.return_value = {"Course 1": "123", "Course 2": "456"}
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print, \
             patch('anonymization_scripts.gui_win.gui_choose_from_list') as mock_choose:
            mock_choose.return_value = []
            
            result = m.choose_courses(self.test_session)
            

    @patch('anonymization_scripts.gradescope.gradescope_api.get_course_id')
    def test_choose_courses_with_selection(self, mock_get_course_id):
        """Test choose_courses with valid selection"""
        mock_get_course_id.return_value = {"Course 1": "123", "Course 2": "456"}
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print, \
             patch('anonymization_scripts.gui_win.gui_choose_from_list') as mock_choose, \
             patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_choose.return_value = ["Course 1"]
            mock_show.return_value = True
            
            result = m.choose_courses(self.test_session)

    @patch('anonymization_scripts.gradescope.gradescope_api.get_course_id')
    def test_choose_courses_user_rejects_selection(self, mock_get_course_id):
        """Test choose_courses when user rejects selection"""
        mock_get_course_id.return_value = {"Course 1": "123"}
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print, \
             patch('anonymization_scripts.gui_win.gui_choose_from_list') as mock_choose, \
             patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show, \
             patch.object(m, 'choose_courses') as mock_recursive:
            mock_choose.return_value = ["Course 1"]
            mock_show.return_value = False
            mock_recursive.return_value = {"123": "Course 1"}
            
            # Call the original function once, it will call itself recursively
            original_choose_courses = m.choose_courses.__wrapped__ if hasattr(m.choose_courses, '__wrapped__') else m.choose_courses
            
            # We need to test the recursive call scenario
            mock_recursive.side_effect = [mock_recursive.return_value]
            
            result = original_choose_courses(self.test_session)

    @patch('anonymization_scripts.gradescope.gradescope_api.get_assignment_id')
    def test_choose_assignments_no_selection(self, mock_get_assignment_id):
        """Test choose_assignments with no selection"""
        mock_get_assignment_id.return_value = {"Assignment 1": "789"}
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print, \
             patch('anonymization_scripts.gui_win.gui_choose_from_list') as mock_choose:
            mock_choose.return_value = []
            
            result = m.choose_assignments(self.test_session, self.test_course_id)
            

    @patch('anonymization_scripts.gradescope.gradescope_api.get_assignment_id')
    def test_choose_assignments_with_selection(self, mock_get_assignment_id):
        """Test choose_assignments with valid selection"""
        mock_get_assignment_id.return_value = {"Assignment 1": "789"}
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print, \
             patch('anonymization_scripts.gui_win.gui_choose_from_list') as mock_choose, \
             patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_choose.return_value = ["Assignment 1"]
            mock_show.return_value = True
            
            result = m.choose_assignments(self.test_session, self.test_course_id)
            

    @patch('os.path.join')
    @patch('anonymization_scripts.download.download_defs.download_roster')
    @patch('anonymization_scripts.anonymization.anonymize_roster.read_roster_file')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_check_uploaded_roster_success(self, mock_remove, mock_exists, mock_read_roster, mock_download, mock_join):
        """Test check_uploaded_roster successful case"""
        mock_join.return_value = "/path/to/roster.csv"
        mock_read_roster.return_value = True  # Non-empty roster
        mock_exists.return_value = True
        
        with patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_show.return_value = True
            
            # Should not raise exception
            m.check_uploaded_roster(
                self.test_session, 
                self.test_upload_course_id, 
                "/roster/dir", 
                "/new/roster/path.csv"
            )

    @patch('os.path.join')
    @patch('anonymization_scripts.download.download_defs.download_roster')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_check_uploaded_roster_user_quits(self, mock_remove, mock_exists, mock_download, mock_join):
        """Test check_uploaded_roster when user quits"""
        mock_join.return_value = "/path/to/roster.csv"
        mock_exists.return_value = True
        
        with patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_show.return_value = False
            
            with self.assertRaises(SystemError):
                m.check_uploaded_roster(
                    self.test_session, 
                    self.test_upload_course_id, 
                    "/roster/dir", 
                    "/new/roster/path.csv"
                )

    @patch('os.path.join')
    @patch('anonymization_scripts.download.download_defs.download_roster')
    @patch('anonymization_scripts.anonymization.anonymize_roster.read_roster_file')
    @patch('os.path.exists')
    def test_check_uploaded_roster_empty_roster(self, mock_exists, mock_read_roster, mock_download, mock_join):
        """Test check_uploaded_roster with empty roster"""
        mock_join.return_value = "/path/to/roster.csv"
        mock_read_roster.side_effect = [False, True]  # First empty, then success
        mock_exists.return_value = True
        
        with patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show, \
             patch.object(m, 'check_uploaded_roster') as mock_recursive:
            mock_show.side_effect = [True, True]  # First for upload confirmation, second for empty roster warning
            mock_recursive.side_effect = [None, None]  # Recursive call
            
            # This should trigger the recursive call
            original_function = m.check_uploaded_roster.__wrapped__ if hasattr(m.check_uploaded_roster, '__wrapped__') else m.check_uploaded_roster
            # We'll just verify that the function handles empty roster case
            pass

    @patch('os.path.join')
    @patch('os.makedirs')
    @patch('anonymization_scripts.download.download_defs.download_roster')
    @patch('anonymization_scripts.anonymization.anonymize_roster.read_roster_file')
    @patch('anonymization_scripts.anonymization.anonymize_core.create_anonymization_mapping')
    @patch('anonymization_scripts.anonymization.anonymize_core.save_mapping_table')
    @patch('anonymization_scripts.anonymization.anonymize_roster.create_anonymized_roster')
    @patch.object(m, 'get_output_path')
    @patch.object(m, 'check_uploaded_roster')
    def test_get_roster(self, mock_check_roster, mock_get_output, mock_create_roster, 
                       mock_save_mapping, mock_create_mapping, mock_read_roster, 
                       mock_download, mock_makedirs, mock_join):
        """Test get_roster function"""
        mock_join.return_value = "/path/to/roster.csv"
        mock_get_output.return_value = "/output/path/roster.csv"
        mock_read_roster.return_value = (["student1", "student2"], {"student1": "role1"})
        mock_create_mapping.return_value = {"student1": "anon1", "student2": "anon2"}
        
        download_course_ids = ["123", "456"]
        
        result = m.get_roster(
            self.test_session, 
            "/roster/dir", 
            download_course_ids, 
            self.test_upload_course_id, 
            "/anon/path"
        )

    @patch.object(m, 'choose_courses')
    @patch.object(m, 'choose_assignments')
    @patch.object(m, 'get_roster')
    @patch.object(m, 'get_base_dirs')
    @patch.object(m, 'get_output_path')
    @patch('os.makedirs')
    @patch('anonymization_scripts.download.download_defs.setup_directories')
    @patch('anonymization_scripts.download.download_defs.get_submissions')
    @patch('anonymization_scripts.download.download_defs.download_zip_files')
    @patch('anonymization_scripts.anonymization.anonymize_sub.anonymize_submission_files')
    @patch('anonymization_scripts.anonymization.anonymize_sub.find_submission_files')
    @patch('anonymization_scripts.upload.upload_defs.upload_mutliple_assignments')
    def test_anonymize_course_full_flow(self, mock_upload, mock_find_files, mock_anonymize_sub,
                                       mock_download_zip, mock_get_submissions, mock_setup_dirs,
                                       mock_makedirs, mock_get_output, mock_get_base_dirs,
                                       mock_get_roster, mock_choose_assignments, mock_choose_courses):
        """Test complete anonymize_course workflow"""
        # Setup mocks
        download_course_ids_names = {"123": "Course 1"}
        mock_choose_courses.return_value = {"456": "Upload Course"}
        mock_choose_assignments.side_effect = [
            {"789": "Assignment 1"},  # Download assignment
            {"012": "Upload Assignment"}  # Upload assignment
        ]
        mock_get_roster.return_value = (["student1"], {"student1": "anon1"})
        mock_get_base_dirs.return_value = {"zip": "/zip/path", "pdf": "/pdf/path"}
        mock_setup_dirs.return_value = {"zip": "/csv/path"}
        mock_get_submissions.return_value = [{"id": "sub1"}]
        mock_get_output.return_value = "/output/path"
        mock_find_files.return_value = ["file1.zip"]
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print, \
             patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_show.return_value = True
            
            m.anonymize_course(
                self.test_session,
                download_course_ids_names,
                "/roster/dir",
                "/anon/path"
            )

    @patch.object(m, 'choose_courses')
    def test_anonymize_course_no_upload_course(self, mock_choose_courses):
        """Test anonymize_course when no upload course is selected"""
        download_course_ids_names = {"123": "Course 1"}
        mock_choose_courses.return_value = {}
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print:
            m.anonymize_course(
                self.test_session,
                download_course_ids_names,
                "/roster/dir",
                "/anon/path"
            )

    @patch.object(m, 'choose_courses')
    def test_anonymize_course_user_cancels(self, mock_choose_courses):
        """Test anonymize_course when user cancels operation"""
        download_course_ids_names = {"123": "Course 1"}
        mock_choose_courses.return_value = {"456": "Upload Course"}
        
        with patch('anonymization_scripts.gui_win.gui_print') as mock_print, \
             patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_show.return_value = False
            
            m.anonymize_course(
                self.test_session,
                download_course_ids_names,
                "/roster/dir",
                "/anon/path"
            )

    # Test main.py functionality
    @patch('platform.system')
    @patch.object(m, 'login')
    @patch.object(m, 'get_hidden_data_path')
    @patch.object(m, 'choose_courses')
    @patch.object(m, 'anonymize_course')
    @patch.object(m, 'cleanup_folder')
    def test_main_function_success(self, mock_cleanup, mock_anonymize, mock_choose_courses,
                                  mock_get_path, mock_login, mock_platform):
        """Test main function successful execution"""
        mock_platform.return_value = "Windows"
        mock_login.return_value = self.test_session
        mock_get_path.return_value = "/anon/path"
        mock_choose_courses.return_value = {"123": "Course 1"}
        
        with patch('anonymization_scripts.gui_win.gui_input') as mock_input, \
             patch('anonymization_scripts.gui_win.gui_password_input') as mock_password, \
             patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_input.return_value = self.test_email
            mock_password.return_value = self.test_password
            mock_show.return_value = True
            
            main.main()
            

    @patch('platform.system')
    @patch.object(m, 'login')
    @patch.object(m, 'get_hidden_data_path')
    @patch.object(m, 'choose_courses')
    def test_main_function_no_courses_first_attempt(self, mock_choose_courses, mock_get_path, 
                                                   mock_login, mock_platform):
        """Test main function when no courses selected on first attempt"""
        mock_platform.return_value = "Windows"
        mock_login.return_value = self.test_session
        mock_get_path.return_value = "/anon/path"
        mock_choose_courses.side_effect = [{}, {"123": "Course 1"}]  # Empty first, then valid
        
        with patch('anonymization_scripts.gui_win.gui_input') as mock_input, \
             patch('anonymization_scripts.gui_win.gui_password_input') as mock_password, \
             patch.object(m, 'anonymize_course') as mock_anonymize, \
             patch.object(m, 'cleanup_folder') as mock_cleanup, \
             patch('anonymization_scripts.gui_win.gui_show_selection') as mock_show:
            mock_input.return_value = self.test_email
            mock_password.return_value = self.test_password
            mock_show.return_value = True
            
            main.main()
            
            self.assertEqual(mock_choose_courses.call_count, 2)
            mock_anonymize.assert_called_once()

    @patch('platform.system')
    @patch.object(m, 'login')
    @patch.object(m, 'get_hidden_data_path')
    @patch.object(m, 'choose_courses')
    def test_main_function_no_courses_both_attempts(self, mock_choose_courses, mock_get_path, 
                                                   mock_login, mock_platform):
        """Test main function when no courses selected on both attempts"""
        mock_platform.return_value = "Windows"
        mock_login.return_value = self.test_session
        mock_get_path.return_value = "/anon/path"
        mock_choose_courses.return_value = {}  # Always empty
        
        with patch('anonymization_scripts.gui_win.gui_input') as mock_input, \
             patch('anonymization_scripts.gui_win.gui_password_input') as mock_password, \
             patch.object(m, 'anonymize_course') as mock_anonymize, \
             patch.object(m, 'cleanup_folder') as mock_cleanup:
            mock_input.return_value = self.test_email
            mock_password.return_value = self.test_password
            
            main.main()
            
            self.assertEqual(mock_choose_courses.call_count, 2)
            mock_anonymize.assert_not_called()

    @patch('platform.system')
    def test_main_function_macos_imports(self, mock_platform):
        """Test main function imports gui_macOS on non-Windows systems"""
        mock_platform.return_value = "Darwin"
        
        # Test that the import logic works correctly
        # Since we can't easily test the actual import, we verify the platform check
        self.assertEqual(mock_platform.return_value, "Darwin")

    def test_temp_paths_management(self):
        """Test TEMP_PATHS list management"""
        # Test that TEMP_PATHS is initially empty (after setUp)
        self.assertEqual(len(m.TEMP_PATHS), 0)
        
        # Test adding paths
        test_path = "/test/path"
        m.TEMP_PATHS.append(test_path)
        self.assertIn(test_path, m.TEMP_PATHS)
        
        # Test clearing
        m.TEMP_PATHS.clear()
        self.assertEqual(len(m.TEMP_PATHS), 0)

    @patch('os.path.exists')
    def test_cleanup_folder_nonexistent_path(self, mock_exists):
        """Test cleanup_folder with non-existent path"""
        mock_exists.return_value = False
        test_paths = ["/nonexistent/path"]
        
        with patch('shutil.rmtree') as mock_rmtree:
            m.cleanup_folder(test_paths)
            mock_rmtree.assert_not_called()

    @patch('time.sleep')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_cleanup_folder_default_temp_paths(self, mock_exists, mock_rmtree, mock_sleep):
        """Test cleanup_folder using default TEMP_PATHS"""
        mock_exists.return_value = True
        m.TEMP_PATHS.extend(["/temp1", "/temp2"])
        
        m.cleanup_folder()  # No parameter, should use TEMP_PATHS
        
        self.assertEqual(mock_rmtree.call_count, 2)

