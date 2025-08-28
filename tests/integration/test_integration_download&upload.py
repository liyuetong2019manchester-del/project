import pytest
import os
import sys
import json
import shutil
import tempfile
import zipfile
from unittest.mock import patch, MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

sys.path.insert(0, os.path.join(project_root, "anonymization_scripts"))

import anonymization_scripts.anonymization.anonymize_core as core
import anonymization_scripts.anonymization.anonymize_roster as roster_anon
import anonymization_scripts.anonymization.anonymize_sub as sub_anon
import anonymization_scripts.download.download_defs as download
import anonymization_scripts.upload.upload_defs as upload
import anonymization_scripts.gradescope.gradescope_api as api
import anonymization_scripts.main as main

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"
TEST_COURSE_ID = "123456"
TEST_ASSIGNMENT_ID = "654321"
TEST_UPLOAD_COURSE_ID = "789012"
TEST_UPLOAD_ASSIGNMENT_ID = "210987"

# Responsible for download module integration testing
class TestDownloadIntegration:
    
    @pytest.fixture
    def setup_download_env(self):
        """Create temporary test environment for download testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create base directories structure
        base_dirs = {
            'zip': os.path.join(temp_dir, 'zip_downloads'),
            'pdf': os.path.join(temp_dir, 'pdf_downloads'),
            'roster': os.path.join(temp_dir, 'roster')
        }
        
        test_env = {
            "temp_dir": temp_dir,
            "base_dirs": base_dirs
        }
        
        yield test_env
        
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_setup_directories(self, setup_download_env):
        """Test directory setup functionality"""
        test_env = setup_download_env
        
        # Test setup_directories function
        csv_paths = download.setup_directories(test_env["base_dirs"])
        
        # Verify directories were created
        for dir_path in test_env["base_dirs"].values():
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)
        
        # Verify CSV paths are correct
        assert 'zip' in csv_paths
        assert 'pdf' in csv_paths
        assert csv_paths['zip'] == os.path.join(test_env["base_dirs"]['zip'], 'raw_zip_index.csv')
        assert csv_paths['pdf'] == os.path.join(test_env["base_dirs"]['pdf'], 'graded_copy_index.csv')
    
    def test_get_submissions(self, mocker, setup_download_env):
        """Test submission retrieval with mocked response"""
        test_env = setup_download_env
        
        # Create mock session and response
        mock_session = MagicMock()
        mock_response = MagicMock()
        
        # Mock HTML content with submission links
        mock_html = """
        <html>
            <table>
                <tr>
                    <td><a href="/submissions/12345">John Doe</a></td>
                </tr>
                <tr>
                    <td><a href="/submissions/67890">Jane Smith</a></td>
                </tr>
                <tr>
                    <td><a href="/other/link">Not a submission</a></td>
                </tr>
            </table>
        </html>
        """
        
        mock_response.text = mock_html
        mock_session.get.return_value = mock_response
        
        # Test get_submissions function
        submissions = download.get_submissions(mock_session, "123456", "654321")
        
        # Verify submissions were extracted correctly
        assert len(submissions) == 2
        assert ("John Doe", "12345") in submissions
        assert ("Jane Smith", "67890") in submissions
        
        # Verify session.get was called with correct URL
        expected_url = "https://www.gradescope.com/courses/123456/assignments/654321/submissions"
        mock_session.get.assert_called_once_with(expected_url)
    
    def test_download_zip_files(self, mocker, setup_download_env):
        """Test ZIP file download functionality"""
        test_env = setup_download_env
        
        # Setup directories
        csv_paths = download.setup_directories(test_env["base_dirs"])
        
        # Create mock session
        mock_session = MagicMock()
        
        # Mock successful ZIP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'PK\x03\x04Mock ZIP content'  # ZIP magic bytes
        mock_session.get.return_value = mock_response
        
        # Test data
        submissions = [("John Doe", "12345"), ("Jane Smith", "67890")]
        
        # Mock time.sleep to speed up test
        mocker.patch('anonymization_scripts.download.download_defs.time.sleep')
        
        # Test download_zip_files function
        download.download_zip_files(
            mock_session, 
            "123456", 
            "654321", 
            submissions, 
            test_env["base_dirs"]['zip'], 
            csv_paths['zip']
        )
        
        # Verify files were created
        expected_files = ["John_Doe_12345.zip", "Jane_Smith_67890.zip"]
        for filename in expected_files:
            file_path = os.path.join(test_env["base_dirs"]['zip'], filename)
            assert os.path.exists(file_path)
            
            # Verify file content
            with open(file_path, 'rb') as f:
                content = f.read()
                assert content == b'PK\x03\x04Mock ZIP content'
        
        # Verify CSV index was created
        assert os.path.exists(csv_paths['zip'])
        
        # Verify CSV content
        with open(csv_paths['zip'], 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3  # Header + 2 data rows
            assert "student_name,submission_id,filename" in lines[0]
    
    def test_download_pdf_files(self, mocker, setup_download_env):
        """Test PDF file download functionality"""
        test_env = setup_download_env
        
        # Setup directories
        csv_paths = download.setup_directories(test_env["base_dirs"])
        
        # Create mock session
        mock_session = MagicMock()
        
        # Mock successful PDF response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'%PDF-1.4Mock PDF content'  # PDF magic bytes
        mock_session.get.return_value = mock_response
        
        # Test data
        submissions = [("John Doe", "12345"), ("Jane Smith", "67890")]
        
        # Mock time.sleep to speed up test
        mocker.patch('anonymization_scripts.download.download_defs.time.sleep')
        
        # Test download_pdf_files function
        download.download_pdf_files(
            mock_session, 
            "123456", 
            "654321", 
            submissions, 
            test_env["base_dirs"]['pdf'], 
            csv_paths['pdf']
        )
        
        # Verify files were created
        expected_files = ["John_Doe_12345.pdf", "Jane_Smith_67890.pdf"]
        for filename in expected_files:
            file_path = os.path.join(test_env["base_dirs"]['pdf'], filename)
            assert os.path.exists(file_path)
            
            # Verify file content
            with open(file_path, 'rb') as f:
                content = f.read()
                assert content == b'%PDF-1.4Mock PDF content'
        
        # Verify CSV index was created
        assert os.path.exists(csv_paths['pdf'])
    
    def test_download_roster(self, mocker, setup_download_env):
        """Test roster download functionality"""
        test_env = setup_download_env
        
        # Create mock session
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"First Name,Last Name,SID,Email,Role\nJohn,Doe,12345,john@example.edu,Student"
        mock_session.get.return_value = mock_response
        
        # Test roster download
        roster_path = os.path.join(test_env["base_dirs"]['roster'], "roster.csv")
        download.download_roster(mock_session, "123456", roster_path)
        
        # Verify file was created
        assert os.path.exists(roster_path)
        
        # Verify content
        with open(roster_path, 'rb') as f:
            content = f.read()
            assert content == b"First Name,Last Name,SID,Email,Role\nJohn,Doe,12345,john@example.edu,Student"
        
        # Verify session.get was called with correct URL
        expected_url = "https://www.gradescope.com/courses/123456/memberships.csv"
        mock_session.get.assert_called_once_with(expected_url)


# Tester C: Responsible for upload module integration testing
class TestUploadIntegration:
    
    @pytest.fixture
    def setup_upload_env(self):
        """Create temporary test environment for upload testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test ZIP file
        zip_path = os.path.join(temp_dir, "John_Doe_12345.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # Add test files to ZIP
            zf.writestr("test_file.py", "print('Hello World')")
            zf.writestr("README.md", "# Test Project")
        
        test_env = {
            "temp_dir": temp_dir,
            "zip_path": zip_path,
            "debug_dir": os.path.join(temp_dir, "debug")
        }
        
        # Create debug directory
        os.makedirs(test_env["debug_dir"])
        
        yield test_env
        
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_extract_name_from_filename(self, setup_upload_env):
        """Test name extraction from filename"""
        test_env = setup_upload_env
        
        # Test various filename formats
        test_cases = [
            ("John_Doe_12345.zip", "John_Doe_12345"),
            ("Jane_Smith_67890.zip", "Jane_Smith_67890"),
            ("test_file.zip", "test_file"),
            ("/path/to/Student_Name_123.zip", "Student_Name_123")
        ]
        
        for filename, expected in test_cases:
            result = upload.extract_name_from_filename(filename)
            assert result == expected
    
    def test_extract_zip_to_temp(self, setup_upload_env):
        """Test ZIP extraction to temporary directory"""
        test_env = setup_upload_env
        
        # Test ZIP extraction
        temp_dir, extracted_files = upload.extract_zip_to_temp(test_env["zip_path"])
        
        try:
            # Verify temporary directory was created
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)
            
            # Verify files were extracted
            assert len(extracted_files) == 2
            
            # Check extracted file paths and content
            file_paths = {rel_path: file_path for file_path, rel_path in extracted_files}
            
            assert "test_file.py" in file_paths
            assert "README.md" in file_paths
            
            # Verify file content
            with open(file_paths["test_file.py"], 'r') as f:
                assert f.read() == "print('Hello World')"
            
            with open(file_paths["README.md"], 'r') as f:
                assert f.read() == "# Test Project"
        
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_get_upload_form_data(self, mocker, setup_upload_env):
        """Test upload form data extraction"""
        test_env = setup_upload_env
        
        # Create mock session and response
        mock_session = MagicMock()
        mock_response = MagicMock()
        
        # Mock HTML with CSRF token and student roster
        mock_html = """
        <html>
            <head>
                <meta name="csrf-token" content="test_csrf_token_123" />
            </head>
            <body>
                <a href="/logout">Log Out</a>
                <script>
                    gon.roster = [
                        {"id": "101", "name": "John Doe"},
                        {"id": "102", "name": "Jane Smith"}
                    ];
                </script>
            </body>
        </html>
        """
        
        mock_response.text = mock_html
        mock_session.get.return_value = mock_response
        
        # Test form data extraction
        csrf_token, student_id = upload.get_upload_form_data(
            mock_session, 
            "https://test.com/upload", 
            "John Doe"
        )
        
        # Verify results
        assert csrf_token == "test_csrf_token_123"
        assert student_id == "101"
        
        # Test with non-existent student
        csrf_token2, student_id2 = upload.get_upload_form_data(
            mock_session, 
            "https://test.com/upload", 
            "Non Existent"
        )
        
        assert csrf_token2 == "test_csrf_token_123"
        assert student_id2 is None
    
    def test_prepare_file_uploads(self, setup_upload_env):
        """Test file upload preparation"""
        test_env = setup_upload_env
        
        # Extract ZIP first
        temp_dir, extracted_files = upload.extract_zip_to_temp(test_env["zip_path"])
        
        try:
            # Test file upload preparation
            files, file_objects = upload.prepare_file_uploads(extracted_files)
            
            # Verify files list structure
            assert len(files) == 2
            assert len(file_objects) == 2
            
            # Check file list format
            for file_entry in files:
                assert len(file_entry) == 2
                assert file_entry[0] == 'submission[files][]'
                assert len(file_entry[1]) == 3  # (filename, file_obj, content_type)
            
            # Verify file objects are readable
            for file_obj in file_objects:
                assert hasattr(file_obj, 'read')
                assert not file_obj.closed
            
            # Clean up file objects
            for file_obj in file_objects:
                file_obj.close()
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_upload_files(self, mocker, setup_upload_env):
        """Test file upload functionality"""
        test_env = setup_upload_env
        
        # Create mock session
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Upload successful"
        mock_session.post.return_value = mock_response
        
        # Mock file preparation
        mock_files = [('submission[files][]', ('test.py', MagicMock(), 'application/octet-stream'))]
        
        # Test upload
        result = upload.upload_files(
            mock_session,
            "https://test.com/upload",
            "test_csrf_token",
            "101",
            mock_files
        )
        
        # Verify upload was called
        assert mock_session.post.called
        
        # Verify response
        assert result.status_code == 200
        assert result.text == "Upload successful"
        
        # Verify POST parameters
        args, kwargs = mock_session.post.call_args
        assert args[0] == "https://test.com/upload"
        assert 'data' in kwargs
        assert 'files' in kwargs
        assert kwargs['data']['authenticity_token'] == "test_csrf_token"
        assert kwargs['data']['submission[owner_id]'] == "101"
    
    def test_verify_upload(self, mocker, setup_upload_env):
        """Test upload verification"""
        test_env = setup_upload_env
        
        # Create mock session and responses
        mock_session = MagicMock()
        
        # Mock successful upload response
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 200
        mock_upload_response.text = "Your submission was received"
        mock_upload_response.headers = {}
        
        # Mock submissions list response
        mock_list_response = MagicMock()
        mock_list_response.text = "John Doe submitted successfully"
        mock_session.get.return_value = mock_list_response
        
        # Test successful verification
        result = upload.verify_upload(
            mock_session,
            "123456",
            "654321",
            mock_upload_response,
            "John Doe",
            test_env["debug_dir"]
        )
        
        assert result == True
        
        # Verify debug files were created
        debug_files = os.listdir(test_env["debug_dir"])
        assert any(f.startswith("upload_response_") for f in debug_files)
        assert any(f.startswith("submissions_list_") for f in debug_files)
    
    def test_upload_single_assignment(self, mocker, setup_upload_env):
        """Test single assignment upload workflow"""
        test_env = setup_upload_env
        
        # Mock all dependencies
        mock_session = MagicMock()
        
        # Mock extract_zip_to_temp
        mock_extracted_files = [("temp/test.py", "test.py")]
        mocker.patch.object(upload, 'extract_zip_to_temp', return_value=(test_env["temp_dir"], mock_extracted_files))
        
        # Mock get_upload_form_data
        mocker.patch.object(upload, 'get_upload_form_data', return_value=("csrf_token", "101"))
        
        # Mock prepare_file_uploads
        mock_files = [('submission[files][]', ('test.py', MagicMock(), 'application/octet-stream'))]
        mock_file_objects = [MagicMock()]
        mocker.patch.object(upload, 'prepare_file_uploads', return_value=(mock_files, mock_file_objects))
        
        # Mock upload_files
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Upload successful"
        mocker.patch.object(upload, 'upload_files', return_value=mock_response)
        
        # Mock verify_upload
        mocker.patch.object(upload, 'verify_upload', return_value=True)
        
        # Mock cleanup_temp_dir
        mocker.patch.object(upload, 'cleanup_temp_dir')
        
        # Mock main.get_output_path
        mocker.patch('anonymization_scripts.upload.upload_defs.main.get_output_path', return_value=test_env["debug_dir"])
        
        # Test upload
        result = upload.upload_single_assignment(
            mock_session,
            "123456",
            "654321",
            test_env["zip_path"]
        )
        
        assert result == True
    
    def test_upload_multiple_assignments(self, mocker, setup_upload_env):
        """Test multiple assignments upload"""
        test_env = setup_upload_env
        
        # Create additional test files
        zip_paths = [test_env["zip_path"]]
        for i in range(2, 4):
            additional_zip = os.path.join(test_env["temp_dir"], f"Student_{i}_ID{i}.zip")
            with zipfile.ZipFile(additional_zip, 'w') as zf:
                zf.writestr(f"file_{i}.py", f"print('Student {i}')")
            zip_paths.append(additional_zip)
        
        # Mock upload_single_assignment to return success
        mocker.patch.object(upload, 'upload_single_assignment', return_value=True)
        
        # Mock time.sleep to speed up test
        mocker.patch('anonymization_scripts.upload.upload_defs.time.sleep')
        
        # Mock GUI function
        mock_gui_show = mocker.patch('anonymization_scripts.upload.upload_defs.gui.gui_show_selection')
        
        # Create mock session
        mock_session = MagicMock()
        
        # Test multiple uploads
        results = upload.upload_mutliple_assignments(
            mock_session,
            "123456",
            "654321",
            zip_paths,
            "Test Download",
            "Test Upload"
        )
        
        # Verify results
        assert len(results) == 3
        for filename, success, status in results:
            assert success == True
            assert status == "✅ Success"
        
        # Verify GUI was called
        mock_gui_show.assert_called_once()
