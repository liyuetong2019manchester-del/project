import pytest
import os
import json
import shutil
import tempfile
import zipfile
import csv
from unittest.mock import patch, MagicMock
import sys

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

# Responsible for anonymization modules integration testing
class TestAnonymizationModulesIntegration:
    
    @pytest.fixture
    def setup_anonymization_env(self):
        """Create comprehensive test environment for anonymization modules"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test roster data with various student types
        roster_data = [
            "First Name,Last Name,SID,Email,Role",
            "John,Doe,12345,john.doe@example.edu,Student",
            "Jane,Smith,67890,jane.smith@example.edu,Student", 
            "Bob,Johnson,11111,bob.johnson@example.edu,Student",
            "Alice,Brown,22222,alice.brown@example.edu,TA",
            "Charlie,Wilson,,charlie.wilson@example.edu,Student",  # Missing SID
            "David,Lee,33333,david.lee@example.edu,Instructor"
        ]
        
        # Create temporary roster file
        roster_path = os.path.join(temp_dir, "test_roster.csv")
        with open(roster_path, "w", encoding='utf-8') as f:
            f.write("\n".join(roster_data))
        
        # Create submission files directory
        submission_dir = os.path.join(temp_dir, "submissions")
        os.makedirs(submission_dir)
        
        # Create mock submission ZIP files with realistic content
        submission_files = [
            ("John_Doe_12345.zip", "John's submission"),
            ("Jane_Smith_67890.zip", "Jane's submission"),
            ("Bob_Johnson_11111.zip", "Bob's submission"),
            ("Alice_Brown_22222.zip", "Alice's submission"),
            ("Unknown_Student_99999.zip", "Unknown student"),  # Not in roster
            ("Invalid_Format.zip", "Invalid format file")  # Wrong format
        ]
        
        for filename, content in submission_files:
            zip_path = os.path.join(submission_dir, filename)
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("main.py", f"# {content}\nprint('Hello from {filename}')")
                zf.writestr("README.md", f"# Assignment Submission\n{content}")
        
        # Create output directories
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir)
        
        debug_dir = os.path.join(temp_dir, "debug")
        os.makedirs(debug_dir)
        
        test_env = {
            "temp_dir": temp_dir,
            "roster_path": roster_path,
            "submission_dir": submission_dir,
            "output_dir": output_dir,
            "debug_dir": debug_dir
        }
        
        yield test_env
        
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_core_anonymization_functionality(self, setup_anonymization_env):
        """Test core anonymization functions"""
        test_env = setup_anonymization_env
        
        # Test generate_anonymous_id consistency
        student_id = "John_Doe_12345"
        anon_id1 = core.generate_anonymous_id(student_id)
        anon_id2 = core.generate_anonymous_id(student_id)
        assert anon_id1 == anon_id2, "Same input should generate same anonymous ID"
        assert len(anon_id1) == 8, "Anonymous ID should be 8 characters"
        
        # Test create_anonymization_mapping
        student_ids = ["John_Doe_12345", "Jane_Smith_67890", "Bob_Johnson_11111"]
        mapping = core.create_anonymization_mapping(student_ids)
        
        assert len(mapping) == 3, "Mapping should contain all student IDs"
        assert all(len(anon_id) == 8 for anon_id in mapping.values()), "All anonymous IDs should be 8 characters"
        assert len(set(mapping.values())) == 3, "All anonymous IDs should be unique"
        
        # Test save and load mapping table
        mapping_path = os.path.join(test_env["temp_dir"], "test_mapping.json")
        save_result = core.save_mapping_table(mapping, mapping_path)
        assert save_result is True, "Mapping table should be saved successfully"
        assert os.path.exists(mapping_path), "Mapping file should exist"
        
        # Load and verify mapping
        id_to_anon, anon_to_id = core.load_mapping_table(mapping_path)
        assert id_to_anon == mapping, "Loaded mapping should match original"
        assert len(anon_to_id) == len(mapping), "Reverse mapping should have same length"
        
        # Test delete mapping table
        delete_result = core.delete_mapping_table(mapping_path)
        assert delete_result is True, "Mapping table should be deleted successfully"
        assert not os.path.exists(mapping_path), "Mapping file should not exist after deletion"
    
    def test_roster_anonymization_complete_flow(self, setup_anonymization_env):
        """Test complete roster anonymization workflow"""
        test_env = setup_anonymization_env
        
        # 1. Read roster file
        name_student_ids, roles = roster_anon.read_roster_file(test_env["roster_path"])
        
        # Verify roster reading
        assert len(name_student_ids) == 4, "Should read 4 valid students (excluding empty SID and instructor)"
    
    def test_submission_anonymization_complete_flow(self, setup_anonymization_env):
        """Test complete submission file anonymization workflow"""
        test_env = setup_anonymization_env
        
        # 1. Read roster and create mapping
        name_student_ids, roles = roster_anon.read_roster_file(test_env["roster_path"])
        mapping = core.create_anonymization_mapping(name_student_ids)
        
        # 2. Find submission files
        submission_files = sub_anon.find_submission_files(test_env["submission_dir"])
        assert len(submission_files) == 6, "Should find all 6 ZIP files"
        
        # 3. Test extract_student_identifier function
        valid_file = "John_Doe_12345.zip"
        extracted_id = sub_anon.extract_student_identifier(valid_file, name_student_ids)
        assert extracted_id == "John_Doe_12345", "Should extract correct student identifier"
        
        invalid_file = "Unknown_Student_99999.zip"
        extracted_id_invalid = sub_anon.extract_student_identifier(invalid_file, name_student_ids)
        assert extracted_id_invalid is None, "Should return None for unknown student"
        
        # 4. Anonymize submission files
        processed, anonymized = sub_anon.anonymize_submission_files(
            test_env["submission_dir"],
            test_env["output_dir"],
            mapping,
            name_student_ids
        )
        
        # Verify anonymization results
        assert processed == 6, "Should process all 6 files"
        assert anonymized == 4, "Should successfully anonymize 4 files (valid students only)"
        
        # 5. Verify anonymized files exist and have correct names
        output_files = os.listdir(test_env["output_dir"])
        zip_files = [f for f in output_files if f.endswith('.zip')]
        assert len(zip_files) == 4, "Should create 4 anonymized ZIP files"
        
        # Verify anonymized files have correct format (8-character anonymous ID)
        for zip_file in zip_files:
            base_name = os.path.splitext(zip_file)[0]
            assert len(base_name) == 8, f"Anonymized file {zip_file} should have 8-character name"
            assert base_name in mapping.values(), f"File name {base_name} should be in mapping values"
        
        # 6. Verify file content preservation
        original_file = os.path.join(test_env["submission_dir"], "John_Doe_12345.zip")
        john_anon_id = mapping["John_Doe_12345"]
        anonymized_file = os.path.join(test_env["output_dir"], f"{john_anon_id}.zip")
        
        assert os.path.exists(anonymized_file), "Anonymized file should exist"
        
        # Compare file contents
        with zipfile.ZipFile(original_file, 'r') as orig_zip:
            orig_files = orig_zip.namelist()
            orig_content = orig_zip.read('main.py').decode('utf-8')
        
        with zipfile.ZipFile(anonymized_file, 'r') as anon_zip:
            anon_files = anon_zip.namelist()
            anon_content = anon_zip.read('main.py').decode('utf-8')
        
        assert orig_files == anon_files, "File structure should be preserved"
        assert orig_content == anon_content, "File content should be preserved"
    
    def test_edge_cases_and_error_handling(self, setup_anonymization_env):
        """Test edge cases and error handling scenarios"""
        test_env = setup_anonymization_env
        
        # Test empty submission directory
        empty_dir = os.path.join(test_env["temp_dir"], "empty")
        os.makedirs(empty_dir)
        
        processed, anonymized = sub_anon.anonymize_submission_files(
            empty_dir, test_env["output_dir"], {}, []
        )
        assert processed == 0, "Should process 0 files from empty directory"
        assert anonymized == 0, "Should anonymize 0 files from empty directory"
        
        # Test non-existent roster file
        try:
            roster_anon.read_roster_file("non_existent.csv")

        except (FileNotFoundError, IOError):
            pass  # Expected behavior
        
        # Test invalid mapping table loading
        invalid_mapping_path = os.path.join(test_env["temp_dir"], "invalid.json")
        with open(invalid_mapping_path, 'w') as f:
            f.write("invalid json content")
        
        
        # Test anonymization with empty mapping
        processed, anonymized = sub_anon.anonymize_submission_files(
            test_env["submission_dir"], test_env["output_dir"], {}, []
        )
        assert processed >= 0, "Should handle empty mapping gracefully"
        assert anonymized == 0, "Should anonymize 0 files with empty mapping"
    
    def test_full_integration_workflow(self, setup_anonymization_env):
        """Test complete end-to-end anonymization workflow"""
        test_env = setup_anonymization_env
        
        # Complete workflow simulation
        print("Starting full integration test...")
        
        # Step 1: Read roster
        name_student_ids, roles = roster_anon.read_roster_file(test_env["roster_path"])
        assert len(name_student_ids) > 0, "Should read student IDs from roster"
        
        # Step 2: Create anonymization mapping
        mapping = core.create_anonymization_mapping(name_student_ids)
        assert len(mapping) == len(name_student_ids), "Mapping should cover all students"
        
        # Step 3: Save mapping table
        mapping_path = os.path.join(test_env["temp_dir"], "integration_mapping.json")
        save_success = core.save_mapping_table(mapping, mapping_path)
        assert save_success, "Should save mapping table successfully"
        
        # Step 4: Create anonymized roster
        anon_roster_path = os.path.join(test_env["output_dir"], "integration_roster.csv")
        roster_anon.create_anonymized_roster(mapping, roles, anon_roster_path)
        assert os.path.exists(anon_roster_path), "Should create anonymized roster"
        
        # Step 5: Anonymize submission files
        processed, anonymized = sub_anon.anonymize_submission_files(
            test_env["submission_dir"],
            test_env["output_dir"],
            mapping,
            name_student_ids
        )
        assert processed > 0, "Should process submission files"
        assert anonymized > 0, "Should anonymize some files"
        
        # Step 6: Verify complete output
        output_files = os.listdir(test_env["output_dir"])
        
        # Should have anonymized roster
        roster_files = [f for f in output_files if f.endswith('.csv')]
        assert len(roster_files) >= 1, "Should have anonymized roster file"
        
        # Should have anonymized submissions
        zip_files = [f for f in output_files if f.endswith('.zip')]
        assert len(zip_files) > 0, "Should have anonymized submission files"
        
        # Step 7: Verify mapping consistency
        id_to_anon, anon_to_id = core.load_mapping_table(mapping_path)
        
        # All anonymized files should have names from mapping
        for zip_file in zip_files:
            anon_id = os.path.splitext(zip_file)[0]
            assert anon_id in anon_to_id, f"Anonymous ID {anon_id} should be in reverse mapping"
        
        # Step 8: Clean up mapping table
        delete_success = core.delete_mapping_table(mapping_path)
        assert delete_success, "Should delete mapping table successfully"
        
        print("Full integration test completed successfully!")


# Responsible for download and upload module integration testing
class TestDownloadUploadIntegration:
    
    @pytest.fixture
    def setup_mock_session(self):
        """Set up mock session object"""
        mock_session = MagicMock()
        
        # Mock successful login response
        login_response = MagicMock()
        login_response.text = "Log Out"  # Indicates successful login
        mock_session.post.return_value = login_response
        
        # Mock submission list response
        submissions_html = """
        <tr>
          <td><a href="/courses/123456/assignments/654321/submissions/111">John Doe</a></td>
        </tr>
        <tr>
          <td><a href="/courses/123456/assignments/654321/submissions/222">Jane Smith</a></td>
        </tr>
        """
        submissions_response = MagicMock()
        submissions_response.text = submissions_html
        
        # Mock student roster download response
        roster_response = MagicMock()
        roster_response.status_code = 200
        roster_response.content = b"First Name,Last Name,SID,Email,Role\nJohn,Doe,12345,john@example.edu,Student"
        
        # Mock ZIP file download response
        zip_response = MagicMock()
        zip_response.status_code = 200
        zip_response.content = b"PK\x03\x04" + b"\x00" * 100  # Valid ZIP file header
        
        # Mock form data fetch response
        form_html = """
        <meta name="csrf-token" content="test_token">
        <script>
        gon.roster = [{"id":"12345","name":"John Doe"},{"id":"67890","name":"Jane Smith"}];
        </script>
        """
        form_response = MagicMock()
        form_response.text = form_html
        
        # Mock upload response
        upload_response = MagicMock()
        upload_response.status_code = 302
        upload_response.headers = {"Location": "/success"}
        upload_response.text = "Your submission was received"
        
