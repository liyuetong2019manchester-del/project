import os
import tempfile
import zipfile
import shutil
import json
import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch, mock_open
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../anonymization_scripts/upload')))
from upload_defs import (
    extract_name_from_filename, 
    extract_zip_to_temp, 
    get_upload_form_data, 
    prepare_file_uploads,
    upload_files,
    verify_upload,
    cleanup_temp_dir,
    upload_single_assignment,
    upload_mutliple_assignments
)


class TestExtractNameFromFilename:
    def test_simple_filename(self):
        filename = "Alice_Smith_12345.zip"
        expected = "Alice_Smith_12345"
        result = extract_name_from_filename(filename)
        assert result == expected

    def test_filename_with_path(self):
        filename = "/some/path/Bob_Jones_67890.zip"
        expected = "Bob_Jones_67890"
        result = extract_name_from_filename(filename)
        assert result == expected

    def test_filename_without_extension(self):
        filename = "Charlie_Wu_99999"
        expected = "Charlie_Wu_99999"
        result = extract_name_from_filename(filename)
        assert result == expected

    def test_filename_with_multiple_dots(self):
        filename = "Dora.Li.version2_54321.zip"
        expected = "Dora.Li.version2_54321"
        result = extract_name_from_filename(filename)
        assert result == expected

    def test_filename_with_unicode(self):
        filename = "张三_李四_12345.zip"
        expected = "张三_李四_12345"
        result = extract_name_from_filename(filename)
        assert result == expected

    def test_empty_filename(self):
        filename = ""
        expected = ""
        result = extract_name_from_filename(filename)
        assert result == expected


class TestExtractZipToTemp:
    @pytest.fixture
    def test_zip_file(self):
        # Create a temporary directory and a ZIP file inside
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "test.zip")
        file_structure = {
            "file1.txt": "Content of file 1",
            "subdir/file2.txt": "Content of file 2"
        }

        # Create files and zip them
        content_dir = os.path.join(temp_dir, "content")
        os.makedirs(content_dir)

        for rel_path, content in file_structure.items():
            full_path = os.path.join(content_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        # Create the zip file
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for rel_path in file_structure:
                full_path = os.path.join(content_dir, rel_path)
                zipf.write(full_path, arcname=rel_path)
        
        yield zip_path, file_structure
        
        # Cleanup
        shutil.rmtree(temp_dir)

    def test_extract_zip_success(self, test_zip_file):
        zip_path, file_structure = test_zip_file
        temp_dir, extracted_files = extract_zip_to_temp(zip_path)

        # Extracted file relative paths
        extracted_rel_paths = set(rel for _, rel in extracted_files)
        expected_rel_paths = set(file_structure.keys())

        assert extracted_rel_paths == expected_rel_paths
        #assert os.path.isdir(temp_dir)

        # Clean up the returned temp_dir manually
        #shutil.rmtree(temp_dir)

    def test_extract_invalid_zip(self, test_zip_file):
        zip_path, _ = test_zip_file
        temp_dir = os.path.dirname(zip_path)
        bad_zip_path = os.path.join(temp_dir, "bad.zip")
        
        with open(bad_zip_path, "w") as f:
            f.write("This is not a valid zip file.")

        with pytest.raises(Exception):
            extract_zip_to_temp(bad_zip_path)

    def test_extract_empty_zip(self):
        # Create an empty zip file
        temp_dir = tempfile.mkdtemp()
        try:
            zip_path = os.path.join(temp_dir, "empty.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                pass  # Create empty zip
            
            extracted_temp_dir, extracted_files = extract_zip_to_temp(zip_path)
            
            assert extracted_files == []
            assert os.path.isdir(extracted_temp_dir)
            
            # Clean up
            shutil.rmtree(extracted_temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    def test_extract_zip_with_nested_dirs(self):
        temp_dir = tempfile.mkdtemp()
        try:
            zip_path = os.path.join(temp_dir, "nested.zip")
            
            # Create nested directory structure
            content_dir = os.path.join(temp_dir, "content")
            nested_dir = os.path.join(content_dir, "level1", "level2")
            os.makedirs(nested_dir)
            
            file_path = os.path.join(nested_dir, "nested_file.txt")
            with open(file_path, "w") as f:
                f.write("nested content")
            
            with zipfile.ZipFile(zip_path, "w") as zipf:
                zipf.write(file_path, arcname="level1/level2/nested_file.txt")
            
            extracted_temp_dir, extracted_files = extract_zip_to_temp(zip_path)
            
            assert len(extracted_files) == 1
            assert extracted_files[0][1] == "level1/level2/nested_file.txt"
            
            # Clean up
            #shutil.rmtree(extracted_temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    @patch('shutil.rmtree')
    def test_extract_zip_cleanup_on_exception(self, mock_rmtree):
        # Test that temp directory is cleaned up when extraction fails
        temp_dir = tempfile.mkdtemp()
        try:
            bad_zip_path = os.path.join(temp_dir, "bad.zip")
            with open(bad_zip_path, "w") as f:
                f.write("This is not a valid zip file.")
            
            with pytest.raises(Exception):
                extract_zip_to_temp(bad_zip_path)
            
            # Verify cleanup was called
            mock_rmtree.assert_called()
        finally:
            shutil.rmtree(temp_dir)


class TestGetUploadFormData:
    @pytest.fixture
    def student_info(self):
        return {
            "name": "Alice Smith",
            "id": 12345
        }
    
    def test_token_from_meta_and_match_student(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        # mock HTML with meta csrf and gon.roster
        roster_json = json.dumps([{"id": student_info["id"], "name": student_info["name"]}])
        html = f"""
        <html>
            <head>
                <meta name="csrf-token" content="csrf_meta_token">
            </head>
            <body>
                Log Out
                <script>gon.roster = {roster_json};</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        assert token == "csrf_meta_token"
        assert sid == student_info["id"]

    def test_token_from_input(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        roster_json = json.dumps([{"id": student_info["id"], "name": student_info["name"]}])
        html = f"""
        <html>
            <body>
                <input type="hidden" name="authenticity_token" value="csrf_input_token" />
                Log Out
                <script>gon.roster = {roster_json};</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        assert token == "csrf_input_token"
        assert sid == student_info["id"]

    def test_expired_session(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        mock_response.text = "<html><body>Login Page</body></html>"
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        assert token is None
        assert sid is None

    def test_no_csrf_token(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        html = f"""
        <html>
            <body>
                Log Out
                <script>gon.roster = [];</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        assert token is None
        assert sid is None

    def test_student_not_found(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        # student name does not match
        other_roster = json.dumps([{"id": 9999, "name": "Not Matching"}])
        html = f"""
        <html>
            <head><meta name="csrf-token" content="csrf_meta_token"></head>
            <body>
                Log Out
                <script>gon.roster = {other_roster};</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        assert token == "csrf_meta_token"
        assert sid is None

    def test_malformed_json_in_roster(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        # Invalid JSON in gon.roster
        html = f"""
        <html>
            <head><meta name="csrf-token" content="csrf_meta_token"></head>
            <body>
                Log Out
                <script>gon.roster = [invalid json];</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        assert token == "csrf_meta_token"
        assert sid is None

    def test_multiple_scripts_with_roster(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        roster_json = json.dumps([{"id": student_info["id"], "name": student_info["name"]}])
        html = f"""
        <html>
            <head><meta name="csrf-token" content="csrf_meta_token"></head>
            <body>
                Log Out
                <script>some other script</script>
                <script>gon.roster = {roster_json};</script>
                <script>another script</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        assert token == "csrf_meta_token"
        assert sid == student_info["id"]

    def test_partial_name_match(self, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        # Test case-insensitive partial matching
        roster_json = json.dumps([{"id": student_info["id"], "name": "ALICE SMITH (Student)"}])
        html = f"""
        <html>
            <head><meta name="csrf-token" content="csrf_meta_token"></head>
            <body>
                Log Out
                <script>gon.roster = {roster_json};</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", "alice smith")
        assert token == "csrf_meta_token"
        assert sid == student_info["id"]

    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('time.time', return_value=1234567890)
    def test_student_not_found_with_debug_save(self, mock_time, mock_json_dump, mock_file, mock_makedirs, student_info):
        mock_session = MagicMock()
        mock_response = MagicMock()

        other_roster = [{"id": 9999, "name": "Not Matching"}]
        roster_json = json.dumps(other_roster)
        html = f"""
        <html>
            <head><meta name="csrf-token" content="csrf_meta_token"></head>
            <body>
                Log Out
                <script>gon.roster = {roster_json};</script>
            </body>
        </html>
        """

        mock_response.text = html
        mock_session.get.return_value = mock_response

        token, sid = get_upload_form_data(mock_session, "https://gradescope.com/fake", student_info["name"])
        
        assert token == "csrf_meta_token"
        assert sid is None
        
        # Verify debug file operations
        mock_makedirs.assert_called_once_with("gradescope_debug", exist_ok=True)
        mock_file.assert_called_once()
        mock_json_dump.assert_called_once_with(other_roster, mock_file(), indent=2)


class TestPrepareFileUploads:
    def test_prepare_file_structure(self):
        # Create a temporary directory and a sample file
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("Sample content")

        try:
            # Simulate extracted file input
            extracted_files = [(file_path, "test.txt")]
            files, file_objs = prepare_file_uploads(extracted_files)

            # Check the structure of the returned 'files' list
            assert len(files) == 1
            assert files[0][0] == 'submission[files][]'
            assert files[0][1][0] == "test.txt"
            assert files[0][1][2] == "application/octet-stream"

            # Check that the file object was opened
            assert len(file_objs) == 1
            assert not file_objs[0].closed

        finally:
            # Clean up: close files and remove temp directory
            for f in file_objs:
                f.close()
            shutil.rmtree(temp_dir)

    def test_prepare_multiple_files(self):
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        try:
            # Create multiple test files
            for i in range(3):
                file_path = os.path.join(temp_dir, f"test{i}.txt")
                with open(file_path, "w") as f:
                    f.write(f"Content {i}")
                file_paths.append(file_path)

            extracted_files = [(path, f"test{i}.txt") for i, path in enumerate(file_paths)]
            files, file_objs = prepare_file_uploads(extracted_files)

            assert len(files) == 3
            assert len(file_objs) == 3
            
            for i, (key, file_tuple) in enumerate(files):
                assert key == 'submission[files][]'
                assert file_tuple[0] == f"test{i}.txt"
                assert file_tuple[2] == "application/octet-stream"

        finally:
            for f in file_objs:
                f.close()
            shutil.rmtree(temp_dir)

    def test_prepare_files_with_backslashes(self):
        temp_dir = tempfile.mkdtemp()
        
        try:
            subdir = os.path.join(temp_dir, "subdir")
            os.makedirs(subdir)
            file_path = os.path.join(subdir, "test.txt")
            with open(file_path, "w") as f:
                f.write("test content")

            # Simulate Windows path with backslashes
            extracted_files = [(file_path, "subdir\\test.txt")]
            files, file_objs = prepare_file_uploads(extracted_files)

            assert len(files) == 1
            # Should convert backslashes to forward slashes
            assert files[0][1][0] == "subdir/test.txt"

        finally:
            for f in file_objs:
                f.close()
            shutil.rmtree(temp_dir)

    @patch('time.sleep')
    def test_prepare_files_with_delay(self, mock_sleep):
        temp_dir = tempfile.mkdtemp()
        
        try:
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w") as f:
                f.write("test content")

            extracted_files = [(file_path, "test.txt")]
            files, file_objs = prepare_file_uploads(extracted_files)

            # Verify sleep was called for delay simulation
            mock_sleep.assert_called_with(0.1)

        finally:
            for f in file_objs:
                f.close()
            shutil.rmtree(temp_dir)


class TestUploadFiles:
    def test_upload_files_success(self):
        # Create a mocked session and response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response

        # Prepare test data
        files = [
            ('submission[files][]', ('test.txt', BytesIO(b"Hello!"), 'application/octet-stream'))
        ]
        csrf_token = "csrf123"
        student_id = "42"
        upload_url = "https://gradescope.com/fake/upload"

        # Call the function
        response = upload_files(mock_session, upload_url, csrf_token, student_id, files)

        # Assertions
        assert response.status_code == 200
        mock_session.post.assert_called_once()

        # Verify form data sent
        args, kwargs = mock_session.post.call_args
        assert kwargs['data']['authenticity_token'] == csrf_token
        assert kwargs['data']['submission[owner_id]'] == student_id
        assert kwargs['files'] == files

    def test_upload_files_without_student_id(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response

        files = [('submission[files][]', ('test.txt', BytesIO(b"Hello!"), 'application/octet-stream'))]
        csrf_token = "csrf123"
        student_id = None  # No student ID
        upload_url = "https://gradescope.com/fake/upload"

        response = upload_files(mock_session, upload_url, csrf_token, student_id, files)

        assert response.status_code == 200
        
        # Verify form data sent without student ID
        args, kwargs = mock_session.post.call_args
        assert kwargs['data']['authenticity_token'] == csrf_token
        assert 'submission[owner_id]' not in kwargs['data']

    def test_upload_files_with_redirect(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_session.post.return_value = mock_response

        files = [('submission[files][]', ('test.txt', BytesIO(b"Hello!"), 'application/octet-stream'))]
        csrf_token = "csrf123"
        student_id = "42"
        upload_url = "https://gradescope.com/fake/upload"

        response = upload_files(mock_session, upload_url, csrf_token, student_id, files)

        # Verify allow_redirects is set to True
        args, kwargs = mock_session.post.call_args
        assert kwargs['allow_redirects'] is True


class TestVerifyUpload:
    @pytest.fixture
    def test_setup(self):
        debug_dir = tempfile.mkdtemp()
        course_id = "123"
        assignment_id = "456"
        student_name = "Alice Smith"
        
        yield debug_dir, course_id, assignment_id, student_name
        
        # Clean up the debug directory
        for f in os.listdir(debug_dir):
            os.remove(os.path.join(debug_dir, f))
        os.rmdir(debug_dir)
    
    def test_verify_upload_success_by_student_name(self, test_setup):
        debug_dir, course_id, assignment_id, student_name = test_setup
        
        # Mock upload response (200 status, contains student name)
        upload_resp = MagicMock()
        upload_resp.status_code = 200
        upload_resp.text = "Submission page: Successfully uploaded"
        upload_resp.headers = {}

        # Mock session.get() to return submissions page with student name
        mock_session = MagicMock()
        submissions_resp = MagicMock()
        submissions_resp.text = "Alice Smith"
        mock_session.get.return_value = submissions_resp

        result = verify_upload(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            upload_resp=upload_resp,
            student_name=student_name,
            debug_dir=debug_dir
        )

        assert result is True

    def test_verify_upload_failure(self, test_setup):
        debug_dir, course_id, assignment_id, student_name = test_setup
        
        # Mock upload response with failed status
        upload_resp = MagicMock()
        upload_resp.status_code = 500
        upload_resp.text = "Internal server error"
        upload_resp.headers = {}

        mock_session = MagicMock()

        result = verify_upload(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            upload_resp=upload_resp,
            student_name=student_name,
            debug_dir=debug_dir
        )

        assert result is False

    def test_verify_upload_success_with_redirect(self, test_setup):
        debug_dir, course_id, assignment_id, student_name = test_setup
        
        # Mock upload response with redirect
        upload_resp = MagicMock()
        upload_resp.status_code = 302
        upload_resp.text = "Redirecting..."
        upload_resp.headers = {'Location': '/courses/123/assignments/456/submissions/789'}

        mock_session = MagicMock()
        
        # Mock redirect response
        redirect_resp = MagicMock()
        redirect_resp.status_code = 200
        
        # Mock submissions list response
        submissions_resp = MagicMock()
        submissions_resp.text = "Alice Smith submission received"
        
        mock_session.get.side_effect = [redirect_resp, submissions_resp]

        result = verify_upload(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            upload_resp=upload_resp,
            student_name=student_name,
            debug_dir=debug_dir
        )

        assert result is True
        assert mock_session.get.call_count == 2

    def test_verify_upload_success_by_response_text(self, test_setup):
        debug_dir, course_id, assignment_id, student_name = test_setup
        
        upload_resp = MagicMock()
        upload_resp.status_code = 200
        upload_resp.text = "Your submission was received successfully"
        upload_resp.headers = {}

        mock_session = MagicMock()
        submissions_resp = MagicMock()
        submissions_resp.text = "No matching student name"
        mock_session.get.return_value = submissions_resp

        result = verify_upload(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            upload_resp=upload_resp,
            student_name=student_name,
            debug_dir=debug_dir
        )

        assert result is True

    def test_verify_upload_with_relative_redirect_url(self, test_setup):
        debug_dir, course_id, assignment_id, student_name = test_setup
        
        upload_resp = MagicMock()
        upload_resp.status_code = 302
        upload_resp.text = "Redirecting..."
        upload_resp.headers = {'Location': '/relative/path'}

        mock_session = MagicMock()
        redirect_resp = MagicMock()
        redirect_resp.status_code = 200
        submissions_resp = MagicMock()
        submissions_resp.text = "Alice Smith"
        
        mock_session.get.side_effect = [redirect_resp, submissions_resp]

        result = verify_upload(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            upload_resp=upload_resp,
            student_name=student_name,
            debug_dir=debug_dir
        )

        # Verify absolute URL was constructed
        calls = mock_session.get.call_args_list
        assert calls[0][0][0] == "https://www.gradescope.com/relative/path"

    def test_verify_upload_no_student_name(self, test_setup):
        debug_dir, course_id, assignment_id, _ = test_setup
        
        upload_resp = MagicMock()
        upload_resp.status_code = 200
        upload_resp.text = "Upload completed"
        upload_resp.headers = {}

        mock_session = MagicMock()
        submissions_resp = MagicMock()
        submissions_resp.text = "Submissions list"
        mock_session.get.return_value = submissions_resp

        result = verify_upload(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            upload_resp=upload_resp,
            student_name=None,  # No student name
            debug_dir=debug_dir
        )

        assert result is False

    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('time.time', return_value=1234567890)
    def test_verify_upload_file_operations(self, mock_time, mock_file, mock_makedirs, test_setup):
        debug_dir, course_id, assignment_id, student_name = test_setup
        
        upload_resp = MagicMock()
        upload_resp.status_code = 500
        upload_resp.text = "Server error"
        upload_resp.headers = {}

        mock_session = MagicMock()

        result = verify_upload(
            session=mock_session,
            course_id=course_id,
            assignment_id=assignment_id,
            upload_resp=upload_resp,
            student_name=student_name,
            debug_dir=debug_dir
        )

        assert result is False
        # Verify debug directory creation and file writing
        mock_makedirs.assert_called_with(debug_dir, exist_ok=True)
        assert mock_file.call_count >= 1  # At least error response file


def test_cleanup_temp_dir_success():
    # Create a temporary directory with a dummy file
    temp_dir = tempfile.mkdtemp()
    debug_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "test.txt")

    with open(file_path, "w") as f:
        f.write("test")

    # Confirm file and directory exist
    assert os.path.exists(temp_dir)
    assert os.path.isfile(file_path)

    try:
        # Run cleanup
        cleanup_temp_dir(temp_dir, debug_dir)

        # Check directory is removed
        assert not os.path.exists(temp_dir)
    finally:
        # Clean debug dir
        if os.path.exists(debug_dir):
            os.rmdir(debug_dir)

def test_cleanup_temp_dir_with_exception():
    # Test cleanup when shutil.rmtree raises an exception
    temp_dir = tempfile.mkdtemp()
    debug_dir = tempfile.mkdtemp()
    
    with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
        # Should not raise exception, just print error
        cleanup_temp_dir(temp_dir, debug_dir)
    
    # Clean up manually
    
        shutil.rmtree(temp_dir)
class TestUploadSingleAssignment:
    @patch("upload_defs.cleanup_temp_dir")
    @patch("upload_defs.verify_upload")
    @patch("upload_defs.upload_files")
    @patch("upload_defs.prepare_file_uploads")
    @patch("upload_defs.get_upload_form_data")
    @patch("upload_defs.extract_zip_to_temp")
    @patch("upload_defs.extract_name_from_filename")
    @patch("upload_defs.get_output_path")  # Assume get_output_path is imported directly
    def test_upload_single_assignment_success(
        self,
        mock_get_output_path,
        mock_extract_name,
        mock_extract_zip,
        mock_get_form,
        mock_prepare_uploads,
        mock_upload_files,
        mock_verify,
        mock_cleanup
    ):
        '''
        # Setup mocks
        session = MagicMock()
        zip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name

        mock_get_output_path.return_value = tempfile.mkdtemp()
        mock_extract_name.return_value = "Alice Smith"
        mock_extract_zip.return_value = ("/tmp/extracted", [("/tmp/extracted/file.txt", "file.txt")])
        mock_get_form.return_value = ("csrf_token_123", "student_id_42")
        mock_prepare_uploads.return_value = (
            [("submission[files][]", ("file.txt", MagicMock(), "application/octet-stream"))],
            [MagicMock()]
        )
        mock_upload_files.return_value = MagicMock(status_code=200, text="successfully uploaded")
        mock_verify.return_value = True

        try:
            # Execute
            result = upload_single_assignment(session, "COURSE123", "ASSIGN456", zip_path)
            assert result is True
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        '''
    def test_upload_single_assignment_file_not_exists(self):
        session = MagicMock()
        non_existent_file = "/path/to/non/existent/file.zip"
        
        result = upload_single_assignment(session, "COURSE123", "ASSIGN456", non_existent_file)
        assert result is False



class TestUploadMultipleAssignments:
    @patch("upload_defs.upload_single_assignment")
    def test_upload_multiple_files(self, mock_single_upload):
        session = MagicMock()
        course_id = "COURSE123"
        assignment_id = "ASSIGN456"

        # Create two fake ZIP files
        temp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        files = [temp1.name, temp2.name]

        try:
            # Mock: one success, one failure
            mock_single_upload.side_effect = [True, False]

            results = upload_mutliple_assignments(session, course_id, assignment_id, files)

            # Assert structure
            assert len(results) == 2
            assert results[0][1] is True
            assert results[1][1] is False
        finally:
            # Cleanup
            for f in [temp1.name, temp2.name]:
                if os.path.exists(f):
                    os.remove(f)

    @patch("upload_defs.upload_single_assignment")
    @patch("time.sleep")
    def test_upload_multiple_with_delays(self, mock_sleep, mock_single_upload):
        session = MagicMock()
        course_id = "COURSE123"
        assignment_id = "ASSIGN456"

        temp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        files = [temp1.name, temp2.name]

        try:
            mock_single_upload.return_value = True

            with patch('gui_win.gui_show_selection') as mock_gui:
                results = upload_mutliple_assignments(session, course_id, assignment_id, files)

            # Verify sleep was called for delays
            assert mock_sleep.call_count >= 2  # At least one sleep per file
            
            # Verify GUI was called with results
            mock_gui.assert_called_once()

        finally:
            for f in [temp1.name, temp2.name]:
                if os.path.exists(f):
                    os.remove(f)

    @patch("upload_defs.upload_single_assignment")
    def test_upload_multiple_with_exception(self, mock_single_upload):
        session = MagicMock()
        course_id = "COURSE123"
        assignment_id = "ASSIGN456"

        temp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        files = [temp1.name]

        try:
            # Mock exception during upload
            mock_single_upload.side_effect = Exception("Upload failed")

            with patch('gui_win.gui_show_selection') as mock_gui:
                results = upload_mutliple_assignments(session, course_id, assignment_id, files)

            assert len(results) == 1
            assert results[0][1] is False  # Should be False due to exception
            assert "Error:" in results[0][2]

        finally:
            if os.path.exists(temp1.name):
                os.remove(temp1.name)

    @patch("upload_defs.upload_single_assignment")
    def test_upload_multiple_with_custom_names(self, mock_single_upload):
        session = MagicMock()
        course_id = "COURSE123"
        assignment_id = "ASSIGN456"
        download_name = "Assignment 1"
        upload_name = "CS101 Assignment"

        temp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        files = [temp1.name]

        try:
            mock_single_upload.return_value = True

            with patch('gui_win.gui_show_selection') as mock_gui:
                results = upload_mutliple_assignments(
                    session, course_id, assignment_id, files, 
                    download_name=download_name, upload_name=upload_name
                )

            # Verify custom names were used in summary
            call_args = mock_gui.call_args[0]
            summary_text = call_args[0]
            assert download_name in summary_text
            assert upload_name in summary_text

        finally:
            if os.path.exists(temp1.name):
                os.remove(temp1.name)

    @patch("upload_defs.upload_single_assignment")
    def test_upload_multiple_success_rate_calculation(self, mock_single_upload):
        session = MagicMock()
        course_id = "COURSE123"
        assignment_id = "ASSIGN456"

        temp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        files = [temp1.name, temp2.name, temp3.name]

        try:
            # Mock: 2 success, 1 failure
            mock_single_upload.side_effect = [True, False, True]

            with patch('gui_win.gui_show_selection'):
                results = upload_mutliple_assignments(session, course_id, assignment_id, files)

            # Verify results structure
            assert len(results) == 3
            success_count = sum(1 for _, success, _ in results if success)
            assert success_count == 2  # 66.7% success rate

        finally:
            for f in [temp1.name, temp2.name, temp3.name]:
                if os.path.exists(f):
                    os.remove(f)

    @patch("upload_defs.upload_single_assignment")
    @patch('platform.system', return_value='Darwin')  # Test macOS branch
    def test_upload_multiple_macos_gui(self, mock_platform, mock_single_upload):
        session = MagicMock()
        course_id = "COURSE123"
        assignment_id = "ASSIGN456"

        temp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        files = [temp1.name]

        try:
            mock_single_upload.return_value = True

            with patch('gui_macOS.gui_show_selection') as mock_gui_macos:
                results = upload_mutliple_assignments(session, course_id, assignment_id, files)

            # Verify macOS GUI was called instead of Windows GUI
            mock_gui_macos.assert_called_once()

        finally:
            if os.path.exists(temp1.name):
                os.remove(temp1.name)
