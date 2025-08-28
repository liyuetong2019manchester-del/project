import os
import shutil
import tempfile
import pytest
import re
import csv
import time
from unittest.mock import MagicMock, patch
import sys
# Add parent directory to sys.path to find download_defs module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../anonymization_scripts/download')))
from download_defs import setup_directories, get_submissions, download_zip_files, download_pdf_files, download_roster


# Test for setup_directories
class TestSetupDirectories:
    @pytest.fixture
    def temp_dir(self):
        # Create a temporary directory for testing
        dir_path = tempfile.mkdtemp()
        yield dir_path
        # Clean up after the test
        shutil.rmtree(dir_path)
    
    @pytest.fixture
    def base_dirs(self, temp_dir):
        return {
            'zip': os.path.join(temp_dir, 'zip_dir'),
            'pdf': os.path.join(temp_dir, 'pdf_dir')
        }
    
    def test_directories_created(self, base_dirs):
        # Call the function with the test base directories
        csv_paths = setup_directories(base_dirs)
        
        # Check if the directories were actually created
        for dir_path in base_dirs.values():
            assert os.path.isdir(dir_path)
        
        # Check if the returned CSV paths are as expected
        expected_csv_paths = {
            'zip': os.path.join(base_dirs['zip'], 'raw_zip_index.csv'),
            'pdf': os.path.join(base_dirs['pdf'], 'graded_copy_index.csv')
        }
        assert csv_paths == expected_csv_paths


# Test for get_submissions
class TestGetSubmissions:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        
        # Prepare a sample HTML response with valid and irrelevant submission links
        sample_html = '''
        <html>
            <body>
                <table>
                    <tr><td><a href="/courses/123/assignments/456/submissions/1001">Alice</a></td></tr>
                    <tr><td><a href="/courses/123/assignments/456/submissions/1002">Bob</a></td></tr>
                    <tr><td><a href="/something/else">Ignore Me</a></td></tr>
                </table>
            </body>
        </html>
        '''
        
        # Make the mock session return the sample HTML
        session.get.return_value.text = sample_html
        return session
    
    def test_get_submissions(self, mock_session):
        course_id = "123"
        assignment_id = "456"
        
        # Define the expected output from the parser
        expected = [('Alice', '1001'), ('Bob', '1002')]
        
        # Call the function under test
        result = get_submissions(mock_session, course_id, assignment_id)
        
        # Verify the returned submissions match what was expected
        assert result == expected
        
        # Check that the correct URL was requested
        expected_url = f'https://www.gradescope.com/courses/{course_id}/assignments/{assignment_id}/submissions'
        mock_session.get.assert_called_once_with(expected_url)


# Test for download_zip_files
class TestDownloadZipFiles:
    @pytest.fixture
    def temp_dir(self):
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path)
    
    @pytest.fixture
    def zip_dir(self, temp_dir):
        zip_dir_path = os.path.join(temp_dir, "zip")
        os.makedirs(zip_dir_path, exist_ok=True)
        return zip_dir_path
    
    @pytest.fixture
    def csv_path(self, temp_dir):
        return os.path.join(temp_dir, "index.csv")
    
    @pytest.fixture
    def submissions(self):
        return [
            ("Alice Smith", "123"),
            ("Bob-Jones", "456"),
            ("Eve.O'Connor", "789")
        ]
    
    @pytest.fixture
    def mock_session(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_zip_content(self):
        return b'PK\x03\x04FakeZipContent'
    
    @pytest.fixture
    def mock_response_success(self, mock_zip_content):
        return MagicMock(status_code=200, content=mock_zip_content)
    
    @pytest.fixture
    def mock_response_fail(self):
        return MagicMock(status_code=404, content=b'Not a zip')
    
    def test_download_zip_files_success(self, mock_session, mock_response_success, submissions, zip_dir, csv_path):
        # Simulate all downloads returning successful ZIP content
        mock_session.get.return_value = mock_response_success
        course_id = "999"
        assignment_id = "888"
        
        # Run the function with the mock session and test data
        download_zip_files(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            submissions=submissions,
            zip_dir=zip_dir,
            csv_path=csv_path
        )
        
        # Check whether 3 ZIP files were created
        zip_files = os.listdir(zip_dir)
        assert len(zip_files) == 3
        
        # Read the CSV file and check its content
        with open(csv_path, newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Expect the CSV to have one header and three records
        assert len(rows) == 4
        assert rows[0] == ['student_name', 'submission_id', 'filename']
    
    def test_download_zip_files_partial_fail(self, mock_session, mock_response_success, mock_response_fail, 
                                           submissions, zip_dir, csv_path):
        # Simulate one success and two failed downloads
        mock_session.get.side_effect = [
            mock_response_success,
            mock_response_fail,
            mock_response_fail
        ]
        
        course_id = "999"
        assignment_id = "888"
        
        # Run the function again with mixed results
        download_zip_files(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            submissions=submissions,
            zip_dir=zip_dir,
            csv_path=csv_path
        )
        
        # Expect only one ZIP file to be created
        zip_files = os.listdir(zip_dir)
        assert len(zip_files) == 1
        
        # Expect the CSV to contain only the header and the one successful record
        with open(csv_path, newline='') as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2


# Test for download_pdf_files
class TestDownloadPdfFiles:
    @pytest.fixture
    def temp_dir(self):
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path)
    
    @pytest.fixture
    def pdf_dir(self, temp_dir):
        pdf_dir_path = os.path.join(temp_dir, "pdf")
        os.makedirs(pdf_dir_path, exist_ok=True)
        return pdf_dir_path
    
    @pytest.fixture
    def csv_path(self, temp_dir):
        return os.path.join(temp_dir, "pdf_index.csv")
    
    @pytest.fixture
    def submissions(self):
        return [
            ("Alice Smith", "123"),
            ("Bob-Jones", "456"),
            ("Eve.O'Connor", "789")
        ]
    
    @pytest.fixture
    def mock_session(self):
        return MagicMock()
    
    @pytest.fixture
    def valid_pdf_content(self):
        return b'%PDF-1.4 fake pdf content'
    
    @pytest.fixture
    def invalid_pdf_content(self):
        return b'Not a pdf'
    
    @pytest.fixture
    def mock_response_success(self, valid_pdf_content):
        return MagicMock(status_code=200, content=valid_pdf_content)
    
    @pytest.fixture
    def mock_response_fail(self, invalid_pdf_content):
        return MagicMock(status_code=404, content=invalid_pdf_content)
    
    @patch("time.sleep", return_value=None)  # Patch time.sleep to avoid slowdowns in tests
    def test_download_pdf_files_success(self, mock_sleep, mock_session, mock_response_success, 
                                      submissions, pdf_dir, csv_path):
        # Simulate all submissions returning valid PDF content
        mock_session.get.return_value = mock_response_success
        course_id = "999"
        assignment_id = "888"
        
        # Call the function under test
        download_pdf_files(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            submissions=submissions,
            pdf_dir=pdf_dir,
            csv_path=csv_path
        )
        
        # Verify that 3 PDF files are created
        pdf_files = os.listdir(pdf_dir)
        assert len(pdf_files) == 3
        
        # Check that the CSV index contains all 3 records plus header
        with open(csv_path, newline='') as f:
            rows = list(csv.reader(f))
        assert len(rows) == 4
        assert rows[0] == ['student_name', 'submission_id', 'filename']
    
    @patch("time.sleep", return_value=None)
    def test_download_pdf_files_partial_fail(self, mock_sleep, mock_session, mock_response_success, 
                                           mock_response_fail, submissions, pdf_dir, csv_path):
        # Simulate one valid response and two invalid ones
        mock_session.get.side_effect = [
            mock_response_success,
            mock_response_fail,
            mock_response_fail
        ]
        
        course_id = "999"
        assignment_id = "888"
        
        # Call the function with mixed responses
        download_pdf_files(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            submissions=submissions,
            pdf_dir=pdf_dir,
            csv_path=csv_path
        )
        
        # Check that only one PDF file is saved
        pdf_files = os.listdir(pdf_dir)
        assert len(pdf_files) == 1
        
        # Check that only the successful submission is recorded in the CSV
        with open(csv_path, newline='') as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2  # Header + 1 record


# Test for download_roster
class TestDownloadRoster:
    @pytest.fixture
    def temp_dir(self):
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path)
    
    @pytest.fixture
    def roster_path(self, temp_dir):
        return os.path.join(temp_dir, "roster.csv")
    
    @pytest.fixture
    def mock_session(self):
        return MagicMock()
    
    @pytest.fixture
    def fake_csv_content(self):
        return b"Name,Email\nAlice,alice@example.com\nBob,bob@example.com"
    
    @pytest.fixture
    def response_success(self, fake_csv_content):
        return MagicMock(status_code=200, content=fake_csv_content)
    
    @pytest.fixture
    def response_fail(self):
        return MagicMock(status_code=403, content=b"")
    
    def test_download_roster_success(self, mock_session, response_success, roster_path):
        # Simulate a successful HTTP response with CSV content
        mock_session.get.return_value = response_success
        course_id = "12345"
        
        # Call the function under test
        download_roster(mock_session, course_id, roster_path)
        
        # Check that the file was created and contains the correct content
        assert os.path.exists(roster_path)
        with open(roster_path, 'rb') as f:
            content = f.read()
        assert content == response_success.content
    
    def test_download_roster_fail(self, mock_session, response_fail, roster_path):
        # Simulate a failed HTTP response
        mock_session.get.return_value = response_fail
        course_id = "12345"
        
        # Call the function under test
        download_roster(mock_session, course_id, roster_path)
        
        # Check that no file was created
        assert not os.path.exists(roster_path)
