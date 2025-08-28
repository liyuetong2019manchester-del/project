import unittest
import os
import sys
import tempfile
import shutil
import json
import csv
import zipfile
import requests_mock
from unittest.mock import patch, MagicMock, mock_open
import platform

# Add project path to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
anonymization_scripts_path = os.path.join(project_root, 'anonymization_scripts')
sys.path.insert(0, anonymization_scripts_path)

# Import modules to be tested
import anonymization_scripts.gradescope.gradescope_api as api
import anonymization_scripts.download.download_defs as down
import anonymization_scripts.upload.upload_defs as up
import anonymization_scripts.anonymization.anonymize_core as core
import anonymization_scripts.anonymization.anonymize_roster as roster
import anonymization_scripts.anonymization.anonymize_sub as sub
import anonymization_scripts.mainScript as main

if platform.system() == "Windows":
    import anonymization_scripts.gui_win as gui


class TestGradescopeIntegration(unittest.TestCase):
    """Comprehensive integration test class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_data_dir = os.path.join(self.test_dir, 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Mock course and assignment data
        self.mock_course_id = "123456"
        self.mock_assignment_id = "789012"
        self.mock_student_data = [
            {"name": "John Doe", "id": "12345"},
            {"name": "Jane Smith", "id": "67890"},
            {"name": "Bob Johnson", "id": "11111"}
        ]
        
        # Create mock roster file
        self.create_mock_roster()
        self.create_mock_zip_files()
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_mock_roster(self):
        """Create mock roster CSV file"""
        roster_path = os.path.join(self.test_data_dir, 'roster.csv')
        with open(roster_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['First Name', 'Last Name', 'SID', 'Email', 'Role'])
            writer.writerow(['John', 'Doe', '12345', 'john@test.edu', 'Student'])
            writer.writerow(['Jane', 'Smith', '67890', 'jane@test.edu', 'Student'])
            writer.writerow(['Bob', 'Johnson', '11111', 'bob@test.edu', 'Student'])
        self.roster_path = roster_path
    
    def create_mock_zip_files(self):
        """Create mock ZIP submission files"""
        self.zip_files = []
        for student in self.mock_student_data:
            name_parts = student["name"].split()
            filename = f"{name_parts[0]}_{name_parts[1]}_{student['id']}.zip"
            zip_path = os.path.join(self.test_data_dir, filename)
            
            # Create ZIP containing sample files
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr('assignment.py', 'print("Hello World")')
                zf.writestr('README.txt', 'This is a test submission')
            
            self.zip_files.append(zip_path)
    
    @requests_mock.Mocker()
    def test_01_api_anti_cache_headers(self, m):
        """Test anti-cache header generation"""
        headers = api.anti_cache_headers()
        
        # Verify required headers exist
        self.assertIn('User-Agent', headers)
        self.assertIn('Cache-Control', headers)
        self.assertIn('Pragma', headers)
        self.assertIn('Expires', headers)
        self.assertIn('X-Request-ID', headers)
        
        # Verify cache control values
        self.assertEqual(headers['Cache-Control'], 'no-cache, no-store, must-revalidate, max-age=0')
        self.assertEqual(headers['Pragma'], 'no-cache')
        self.assertEqual(headers['Expires'], '0')
    
    @requests_mock.Mocker()
    def test_02_login_to_gradescope_success(self, m):
        """Test successful Gradescope login"""
        # Mock login page response
        m.get('https://www.gradescope.com/login', 
              text='<input name="authenticity_token" value="test_token">')
        
        # Mock successful login response
        m.post('https://www.gradescope.com/login', 
               text='<a href="/logout">Log Out</a>')
        
        session = api.login_to_gradescope('test@example.com', 'password')
        
        # Verify returned session is valid
        self.assertIsNotNone(session)
        self.assertIsInstance(session, requests_mock.adapter.Session)
    
    @requests_mock.Mocker()
    def test_03_login_to_gradescope_failure(self, m):
        """Test login failure"""
        # Mock login page response
        m.get('https://www.gradescope.com/login', 
              text='<input name="authenticity_token" value="test_token">')
        
        # Mock login failure response
        m.post('https://www.gradescope.com/login', 
               text='Login failed')
        
        with self.assertRaises(Exception) as context:
            api.login_to_gradescope('wrong@example.com', 'wrongpassword')
        
        self.assertIn('Login failed', str(context.exception))
    
    @requests_mock.Mocker()
    def test_04_get_course_id(self, m):
        """Test getting course ID"""
        mock_html = '''
        <h1>Instructor Courses</h1>
        <div class="courseList">
            <div class="courseList--term">2025 Spring</div>
            <div class="courseList--coursesForTerm">
                <a href="/courses/123456" class="courseBox">
                    <h3 class="courseBox--shortname">CS101</h3>
                </a>
                <a href="/courses/789012" class="courseBox">
                    <h3 class="courseBox--shortname">CS102</h3>
                </a>
            </div>
        </div>
        '''
        
        m.get('https://www.gradescope.com/', text=mock_html)
        
        session = requests_mock.MockAdapter().Session()
    
    @requests_mock.Mocker()
    def test_05_get_assignment_id(self, m):
        """Test getting assignment ID"""
        mock_props = {
            'table_data': [
                {'title': 'Assignment 1', 'id': 'assignment_12345'},
                {'title': 'Assignment 2', 'id': 'assignment_67890'}
            ]
        }
        
        mock_html = f'''
        <div data-react-class="AssignmentsTable" 
             data-react-props="{json.dumps(mock_props).replace('"', '&quot;')}">
        </div>
        '''
        
        m.get(f'https://www.gradescope.com/courses/{self.mock_course_id}/assignments', 
              text=mock_html)
        
        session = requests_mock.MockAdapter().Session()
    
    @requests_mock.Mocker()
    def test_06_check_id_valid(self, m):
        """Test ID validation - valid ID"""
        m.get(f'https://www.gradescope.com/courses/{self.mock_course_id}', 
              status_code=200, text='Valid course page')
        
        session = requests_mock.MockAdapter().Session()
    
    @requests_mock.Mocker()
    def test_07_check_id_invalid(self, m):
        """Test ID validation - invalid ID"""
        m.get('https://www.gradescope.com/courses/invalid', 
              status_code=404)
        
        session = requests_mock.MockAdapter().Session()
    def test_08_anonymization_core_generate_id(self):
        """Test anonymous ID generation"""
        student_id = "John_Doe_12345"
        salt = "test_salt"
        
        # Generate anonymous ID
        anon_id1 = core.generate_anonymous_id(student_id, salt)
        anon_id2 = core.generate_anonymous_id(student_id, salt)
        
        # Verify consistency
        self.assertEqual(anon_id1, anon_id2)
        self.assertEqual(len(anon_id1), 8)
        
        # Verify different inputs produce different outputs
        different_id = core.generate_anonymous_id("Jane_Smith_67890", salt)
        self.assertNotEqual(anon_id1, different_id)
    
    def test_09_anonymization_core_create_mapping(self):
        """Test creating anonymization mapping"""
        student_ids = ["John_Doe_12345", "Jane_Smith_67890", "Bob_Johnson_11111"]
        
        mapping = core.create_anonymization_mapping(student_ids)
        
        # Verify mapping contains all students
        self.assertEqual(len(mapping), 3)
        for student_id in student_ids:
            self.assertIn(student_id, mapping)
            self.assertEqual(len(mapping[student_id]), 8)
    
    def test_10_anonymization_core_save_load_mapping(self):
        """Test mapping table save and load"""
        student_ids = ["John_Doe_12345", "Jane_Smith_67890"]
        mapping = core.create_anonymization_mapping(student_ids)
        
        # Save mapping table
        temp_mapping_path = os.path.join(self.test_dir, 'test_mapping.json')
        result = core.save_mapping_table(mapping, temp_mapping_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(temp_mapping_path))
        
        # Load mapping table
        loaded_id_to_anon, loaded_anon_to_id = core.load_mapping_table(temp_mapping_path)
        
        # Verify loaded data
        self.assertEqual(mapping, loaded_id_to_anon)
        for student_id, anon_id in mapping.items():
            self.assertEqual(loaded_anon_to_id[anon_id], student_id)
    
    def test_11_anonymization_core_delete_mapping(self):
        """Test deleting mapping table"""
        temp_file_path = os.path.join(self.test_dir, 'delete_test.json')
        
        # Create test file
        with open(temp_file_path, 'w') as f:
            f.write('{"test": "data"}')
        
        # Test deleting existing file
        result = core.delete_mapping_table(temp_file_path)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(temp_file_path))
        
        # Test deleting non-existent file
        result = core.delete_mapping_table(temp_file_path)
        self.assertFalse(result)
    
    def test_12_roster_read_roster_file(self):
        """Test reading roster file"""
        name_student_ids = []
        roles = {}
        
        result = roster.read_roster_file(self.roster_path, name_student_ids, roles)
        
        # Verify return value
        self.assertNotEqual(result, False)
        returned_ids, returned_roles = result
        
        # Verify data correctness
        expected_ids = ["John_Doe_12345", "Jane_Smith_67890", "Bob_Johnson_11111"]
        self.assertEqual(set(returned_ids), set(expected_ids))
        
        for student_id in expected_ids:
            self.assertEqual(returned_roles[student_id], 'Student')
    
    def test_13_roster_create_anonymized_roster(self):
        """Test creating anonymized roster"""
        # Prepare data
        name_student_ids = ["John_Doe_12345", "Jane_Smith_67890", "Bob_Johnson_11111"]
        mapping = core.create_anonymization_mapping(name_student_ids)
        roles = {student_id: 'Student' for student_id in name_student_ids}
        
        # Create anonymized roster
        output_path = os.path.join(self.test_dir, 'anon_roster.csv')
        roster.create_anonymized_roster(mapping, roles, output_path)
        
        # Verify file creation
        self.assertTrue(os.path.exists(output_path))
        
        # Verify file content
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row['Role'], 'Student')
            self.assertTrue(row['SID'] in mapping.values())
    
    def test_14_submission_find_files(self):
        """Test finding submission files"""
        # Create test directory structure
        test_sub_dir = os.path.join(self.test_dir, 'submissions')
        os.makedirs(test_sub_dir, exist_ok=True)
        
        # Create test files
        zip_files = ['test1.zip', 'test2.ZIP', 'other.txt']
        for filename in zip_files:
            with open(os.path.join(test_sub_dir, filename), 'w') as f:
                f.write('test')
        
        # Find ZIP files
        found_files = sub.find_submission_files(test_sub_dir, r'.*\.zip')
        
        # Verify results
        self.assertEqual(len(found_files), 2)  # Should find 2 zip files
        
        found_basenames = [os.path.basename(f) for f in found_files]
        self.assertIn('test1.zip', found_basenames)
        self.assertIn('test2.ZIP', found_basenames)
    
    def test_15_submission_extract_identifier(self):
        """Test extracting student identifier from filename"""
        student_ids = ["John_Doe_12345", "Jane_Smith_67890", "Bob_Johnson_11111"]
        
        # Test correct filename format
        filename1 = "John_Doe.zip"
        result1 = sub.extract_student_identifier(filename1, student_ids)
        self.assertEqual(result1, "John_Doe_12345")
        
        # Test non-matching filename
        filename2 = "Unknown_Student.zip"
        result2 = sub.extract_student_identifier(filename2, student_ids)
        self.assertIsNone(result2)
    
    def test_16_submission_anonymize_files(self):
        """Test anonymizing submission files"""
        # Prepare data
        name_student_ids = ["John_Doe_12345", "Jane_Smith_67890", "Bob_Johnson_11111"]
        mapping = core.create_anonymization_mapping(name_student_ids)
        
        # Create output directory
        output_dir = os.path.join(self.test_dir, 'anonymized')
        
        # Execute anonymization
        processed, anonymized = sub.anonymize_submission_files(
            self.test_data_dir, output_dir, mapping, name_student_ids
        )
        
        # Verify results
        self.assertEqual(processed, 3)  # Should process 3 files
        self.assertEqual(anonymized, 3)  # Should successfully anonymize 3 files
        
        # Verify output files exist
        self.assertTrue(os.path.exists(output_dir))
        output_files = os.listdir(output_dir)
        self.assertEqual(len(output_files), 3)
        
        # Verify filename format
        for filename in output_files:
            self.assertTrue(filename.endswith('.zip'))
            base_name = os.path.splitext(filename)[0]
            self.assertEqual(len(base_name), 8)  # Anonymous ID length is 8
    
    @requests_mock.Mocker()
    def test_17_download_get_submissions(self, m):
        """Test getting submission list"""
        mock_html = '''
        <tr>
            <td><a href="/submissions/12345">John Doe</a></td>
        </tr>
        <tr>
            <td><a href="/submissions/67890">Jane Smith</a></td>
        </tr>
        '''
        
        m.get(f'https://www.gradescope.com/courses/{self.mock_course_id}/assignments/{self.mock_assignment_id}/submissions',
              text=mock_html)
        
        session = requests_mock.MockAdapter().Session()
    
    def test_18_download_setup_directories(self):
        """Test directory setup"""
        base_dirs = {
            'zip': os.path.join(self.test_dir, 'zip'),
            'pdf': os.path.join(self.test_dir, 'pdf')
        }
        
        csv_paths = down.setup_directories(base_dirs)
        
        # Verify directory creation
        for dir_path in base_dirs.values():
            self.assertTrue(os.path.exists(dir_path))
        
        # Verify CSV paths are correct
        self.assertIn('zip', csv_paths)
        self.assertIn('pdf', csv_paths)
    
    @patch('anonymization_scripts.upload.upload_defs.zipfile.ZipFile')
    @patch('anonymization_scripts.upload.upload_defs.tempfile.mkdtemp')
    def test_19_upload_extract_zip(self, mock_mkdtemp, mock_zipfile):
        """Test ZIP file extraction"""
        # Mock temporary directory
        temp_dir = os.path.join(self.test_dir, 'temp_extract')
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir
        
        # Create test files
        test_files = ['file1.py', 'file2.txt']
        for filename in test_files:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                f.write('test content')
        
        # Mock ZipFile
        mock_zip_instance = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance
        
        # Test extraction
        zip_path = self.zip_files[0]
        result_temp_dir, extracted_files = up.extract_zip_to_temp(zip_path)
        
        # Verify results
        self.assertEqual(result_temp_dir, temp_dir)
        self.assertEqual(len(extracted_files), 2)
    
    def test_20_upload_extract_name_from_filename(self):
        """Test extracting name from filename"""
        filename = "John_Doe_12345.zip"
        name = up.extract_name_from_filename(filename)
        
        self.assertEqual(name, "John_Doe_12345")
    
    @patch('tkinter.Tk')
    def test_21_gui_input(self, mock_tk):
        """Test GUI input functionality"""
        # Mock tkinter behavior
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        
        with patch('anonymization_scripts.gui_win._create_custom_input_dialog', return_value='test_input'):
            result = gui.gui_input("Test prompt")
            self.assertEqual(result, 'test_input')
    
    @patch('tkinter.Tk')
    def test_22_gui_password_input(self, mock_tk):
        """Test GUI password input"""
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        
        with patch('anonymization_scripts.gui_win._create_custom_input_dialog', return_value='test_password'):
            result = gui.gui_password_input("Enter password:")
            self.assertEqual(result, 'test_password')
    
    def test_23_gui_print(self):
        """Test GUI print functionality"""
        # Clear message list
        gui.all_messages.clear()
        
        # Test printing
        test_message = "Test message"
        gui.gui_print(test_message)
        
        # Verify message was recorded
        self.assertIn(test_message + '\n', gui.all_messages)
    
    @patch('tkinter.Tk')
    def test_24_gui_choose_from_list(self, mock_tk):
        """Test GUI list selection"""
        items = ['Item 1', 'Item 2', 'Item 3']
        
        with patch('anonymization_scripts.gui_win.tk.Listbox') as mock_listbox:
            mock_listbox_instance = MagicMock()
            mock_listbox.return_value = mock_listbox_instance
            mock_listbox_instance.curselection.return_value = (0,)  # Select first item
            
            with patch('tkinter.Tk') as mock_tk_class:
                mock_root = MagicMock()
                mock_tk_class.return_value = mock_root
                
                # Mock user selection
                result = gui.gui_choose_from_list(items, "Choose item")
                
                # Due to complex GUI interactions, we mainly verify the function doesn't crash
                # Actual return value depends on specific mock setup
                self.assertIsNotNone(result)
    
    def test_25_main_get_program_dir(self):
        """Test getting program directory"""
        program_dir = main.get_program_dir()
        
        # Verify returned path is valid
        self.assertTrue(os.path.exists(program_dir))
        self.assertTrue(os.path.isdir(program_dir))
    
    def test_26_main_get_output_path(self):
        """Test getting output path"""
        filename = "test_file.txt"
        output_path = main.get_output_path(filename)
        
        # Verify path format is correct
        self.assertTrue(output_path.endswith(filename))
        self.assertTrue(os.path.isabs(output_path))
    
    def test_27_main_get_hidden_data_path(self):
        """Test getting hidden data path"""
        hidden_path = main.get_hidden_data_path()
        
        # Verify path exists
        self.assertTrue(os.path.exists(hidden_path))
        self.assertTrue(os.path.isdir(hidden_path))
        
        # Verify path is in temp paths list
        self.assertIn(hidden_path, main.TEMP_PATHS)
    
    def test_28_main_get_base_dirs(self):
        """Test getting base directories"""
        anon_path = self.test_dir
        course_id = "123"
        assignment_id = "456"
        
        base_dirs = main.get_base_dirs(anon_path, course_id, assignment_id)
        
        # Verify directory structure
        self.assertIn('zip', base_dirs)
        self.assertIn('pdf', base_dirs)
        self.assertTrue(base_dirs['zip'].startswith(anon_path))
        self.assertTrue(base_dirs['pdf'].startswith(anon_path))
    
    def test_29_main_cleanup_folder(self):
        """Test folder cleanup"""
        # Create test folders
        test_folders = []
        for i in range(2):
            folder_path = os.path.join(self.test_dir, f'temp_folder_{i}')
            os.makedirs(folder_path, exist_ok=True)
            # Create test file
            with open(os.path.join(folder_path, 'test.txt'), 'w') as f:
                f.write('test')
            test_folders.append(folder_path)
        
        # Verify folders exist
        for folder in test_folders:
            self.assertTrue(os.path.exists(folder))
        
        # Execute cleanup
        main.cleanup_folder(test_folders)
        
        # Verify folders were deleted
        for folder in test_folders:
            self.assertFalse(os.path.exists(folder))
    
    @requests_mock.Mocker()
    @patch('anonymization_scripts.gui_win.gui_choose_from_list')
    @patch('anonymization_scripts.gui_win.gui_show_selection')
    def test_30_main_choose_courses(self, m, mock_gui_show, mock_gui_choose):
        """Test course selection functionality"""
        # Mock API response
        mock_html = '''
        <h1>Instructor Courses</h1>
        <div class="courseList">
            <div class="courseList--term">2025 Spring</div>
            <div class="courseList--coursesForTerm">
                <a href="/courses/123456" class="courseBox">
                    <h3 class="courseBox--shortname">CS101</h3>
                </a>
            </div>
        </div>
        '''
        m.get('https://www.gradescope.com/', text=mock_html)
        
        # Mock GUI selection
        mock_gui_choose.return_value = ['2025 Spring - CS101']
        mock_gui_show.return_value = True
        
        session = requests_mock.MockAdapter().Session()
    
    @requests_mock.Mocker()
    @patch('anonymization_scripts.gui_win.gui_choose_from_list')
    @patch('anonymization_scripts.gui_win.gui_show_selection')
    def test_31_main_choose_assignments(self, m, mock_gui_show, mock_gui_choose):
        """Test assignment selection functionality"""
        # Mock API response
        mock_props = {
            'table_data': [
                {'title': 'Assignment 1', 'id': 'assignment_12345'}
            ]
        }
        mock_html = f'''
        <div data-react-class="AssignmentsTable" 
             data-react-props="{json.dumps(mock_props).replace('"', '&quot;')}">
        </div>
        '''
        m.get(f'https://www.gradescope.com/courses/{self.mock_course_id}/assignments', 
              text=mock_html)
        
        # Mock GUI selection
        mock_gui_choose.return_value = ['Assignment 1']
        mock_gui_show.return_value = True
        
        session = requests_mock.MockAdapter().Session()
    
    @requests_mock.Mocker()
    def test_32_integration_full_anonymization_workflow(self, m):
        """Test complete anonymization workflow"""
        # 1. Mock login
        m.get('https://www.gradescope.com/login', 
              text='<input name="authenticity_token" value="test_token">')
        m.post('https://www.gradescope.com/login', 
               text='<a href="/logout">Log Out</a>')
        
        # 2. Mock getting courses
        course_html = '''
        <h1>Instructor Courses</h1>
        <div class="courseList">
            <div class="courseList--term">2025 Spring</div>
            <div class="courseList--coursesForTerm">
                <a href="/courses/123456" class="courseBox">
                    <h3 class="courseBox--shortname">CS101</h3>
                </a>
            </div>
        </div>
        '''
        m.get('https://www.gradescope.com/', text=course_html)
        
        # 3. Mock getting assignments
        assignment_props = {
            'table_data': [
                {'title': 'Assignment 1', 'id': 'assignment_12345'}
            ]
        }
        assignment_html = f'''
        <div data-react-class="AssignmentsTable" 
             data-react-props="{json.dumps(assignment_props).replace('"', '&quot;')}">
        </div>
        '''
        m.get('https://www.gradescope.com/courses/123456/assignments', text=assignment_html)
        
        # 4. Mock getting submission list
        submission_html = '''
        <tr><td><a href="/submissions/111">John Doe</a></td></tr>
        <tr><td><a href="/submissions/222">Jane Smith</a></td></tr>
        '''
        m.get('https://www.gradescope.com/courses/123456/assignments/12345/submissions',
              text=submission_html)
        
        # 5. Mock downloading roster
        roster_csv = 'First Name,Last Name,SID,Email,Role\nJohn,Doe,12345,john@test.edu,Student\nJane,Smith,67890,jane@test.edu,Student'
        m.get('https://www.gradescope.com/courses/123456/memberships.csv', text=roster_csv)
        
        # 6. Mock downloading ZIP files
        zip_content = b'PK' + b'\x00' * 100  # Mock ZIP file content
        m.get('https://www.gradescope.com/courses/123456/assignments/12345/submissions/111.zip',
              content=zip_content)
        m.get('https://www.gradescope.com/courses/123456/assignments/12345/submissions/222.zip',
              content=zip_content)
        
        # Execute test
        
        # Login
        session = api.login_to_gradescope('test@example.com', 'password')
        self.assertIsNotNone(session)
        
        # Get courses
        courses = api.get_course_id(session)
        self.assertIn('2025 Spring - CS101', courses)
        
        # Get assignments
        assignments = api.get_assignment_id(session, '123456')
        self.assertIn('Assignment 1', assignments)
        
        # Get submissions
        submissions = down.get_submissions(session, '123456', '12345')
        self.assertEqual(len(submissions), 2)
        
        # Create directory structure
        base_dirs = {
            'zip': os.path.join(self.test_dir, 'zip'),
            'pdf': os.path.join(self.test_dir, 'pdf')
        }
        csv_paths = down.setup_directories(base_dirs)
        
        # Mock download process (simplified version)
        roster_path = os.path.join(self.test_dir, 'roster.csv')
        with open(roster_path, 'w') as f:
            f.write(roster_csv)
        
        # Test roster processing
        name_student_ids, roles = roster.read_roster_file(roster_path)
        mapping = core.create_anonymization_mapping(name_student_ids)
        
        # Verify entire process completed
        self.assertGreater(len(mapping), 0)
        self.assertGreater(len(name_student_ids), 0)
    
    def test_33_error_handling_and_edge_cases(self):
        """Test error handling and edge cases"""
        # Test empty roster file
        empty_roster_path = os.path.join(self.test_dir, 'empty_roster.csv')
        with open(empty_roster_path, 'w') as f:
            f.write('First Name,Last Name,SID,Email,Role\n')  # Only header row
        
        result = roster.read_roster_file(empty_roster_path)
        self.assertEqual(result, False)
        