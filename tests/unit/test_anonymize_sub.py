import pytest
import sys
import os
import shutil

# Add module path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../anonymization_scripts/anonymization')))
from anonymize_sub import find_submission_files, extract_student_identifier, anonymize_submission_files  # type: ignore

# Fixed variables for test data and directories
TEST_SUBMISSION_DIR = "test_submissions"
TEST_OUTPUT_DIR = "test_output"

@pytest.fixture
def test_data():
    """
    Set up test data and directories
    """
    # Test data
    test_student_ids = [
        "John_Doe_12345",
        "Jane_Smith_67890",
        "Alice_Wonder_54321"
    ]
    test_mapping = {
        "John_Doe_12345": "anon1234",
        "Jane_Smith_67890": "anon5678",
        "Alice_Wonder_54321": "anon9101"
    }
    
    # Create test submission directory
    os.makedirs(TEST_SUBMISSION_DIR, exist_ok=True)
    with open(os.path.join(TEST_SUBMISSION_DIR, "John_Doe.zip"), "w") as f:
        f.write("Test content for John Doe")
    with open(os.path.join(TEST_SUBMISSION_DIR, "Jane_Smith.zip"), "w") as f:
        f.write("Test content for Jane Smith")
    with open(os.path.join(TEST_SUBMISSION_DIR, "Unknown_User.zip"), "w") as f:
        f.write("Test content for Unknown User")
    
    # Return test data
    yield {
        "student_ids": test_student_ids,
        "mapping": test_mapping
    }
    
    # Clean up test directories
    if os.path.exists(TEST_SUBMISSION_DIR):
        shutil.rmtree(TEST_SUBMISSION_DIR)
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)

def test_find_submission_files(test_data):
    """
    Test if find_submission_files function correctly finds files matching the pattern
    """
    files = find_submission_files(TEST_SUBMISSION_DIR, pattern=r'.*\.zip')
    assert len(files) == 3, "Should find 3 .zip files"
    assert any("John_Doe.zip" in file for file in files), "Should include John_Doe.zip"
    assert any("Jane_Smith.zip" in file for file in files), "Should include Jane_Smith.zip"
    assert any("Unknown_User.zip" in file for file in files), "Should include Unknown_User.zip"

def test_extract_student_identifier(test_data):
    """
    Test if extract_student_identifier function correctly extracts student identifiers
    """
    student_ids = test_data["student_ids"]
    
    # Test known students
    student_id = extract_student_identifier("John_Doe.zip", student_ids)
    assert student_id == "John_Doe_12345", "Should correctly match John_Doe_12345"
    
    student_id = extract_student_identifier("Jane_Smith.zip", student_ids)
    assert student_id == "Jane_Smith_67890", "Should correctly match Jane_Smith_67890"
    
    # Test unknown student
    student_id = extract_student_identifier("Unknown_User.zip", student_ids)
    assert student_id is None, "Unknown user should return None"

def test_anonymize_submission_files(test_data):
    """
    Test if anonymize_submission_files function correctly anonymizes files
    """
    student_ids = test_data["student_ids"]
    mapping = test_data["mapping"]
    
    processed_count, anonymized_count = anonymize_submission_files(
        TEST_SUBMISSION_DIR,
        TEST_OUTPUT_DIR,
        mapping,
        student_ids
    )
    
    assert processed_count == 3, "Should process 3 files"
    assert anonymized_count == 2, "Should successfully anonymize 2 files"
    
    # Check if output directory contains anonymized files
    output_files = os.listdir(TEST_OUTPUT_DIR)
    assert "anon1234.zip" in output_files, "Should include anonymized file anon1234.zip"
    assert "anon5678.zip" in output_files, "Should include anonymized file anon5678.zip"
    assert "Unknown_User.zip" not in output_files, "Unknown user file should not be anonymized"

# Add more tests to increase coverage
def test_find_submission_files_empty_dir(tmp_path):
    """
    Test find_submission_files on an empty directory
    """
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    files = find_submission_files(str(empty_dir))
    assert len(files) == 0, "Empty directory should return an empty list"

def test_find_submission_files_nonexistent_dir():
    """
    Test find_submission_files on a non-existent directory
    """
    files = find_submission_files("nonexistent_directory")
    assert len(files) == 0, "Non-existent directory should return an empty list"

def test_extract_student_identifier_edge_cases(test_data):
    """
    Test edge cases for extract_student_identifier
    """
    student_ids = test_data["student_ids"]
    
    # Test empty filename
    student_id = extract_student_identifier("", student_ids)
    assert student_id is None, "Empty filename should return None"
    
    # Test partial match (not exact match)
    student_id = extract_student_identifier("John.zip", student_ids)
    assert student_id is None or student_id == "John_Doe_12345", "Partial match should return None or correct match"
    
    # Test case insensitivity
    student_id = extract_student_identifier("john_doe.zip", student_ids)
    assert student_id == "John_Doe_12345", "Case insensitive match should match correctly"

def test_anonymize_submission_files_target_dir_creation():
    """
    Test if target directory is created correctly when it doesn't exist
    """
    # Set up test data
    test_student_ids = ["John_Doe_12345"]
    test_mapping = {"John_Doe_12345": "anon1234"}
    
    # Create test submission directory and file
    os.makedirs(TEST_SUBMISSION_DIR, exist_ok=True)
    with open(os.path.join(TEST_SUBMISSION_DIR, "John_Doe.zip"), "w") as f:
        f.write("Test content")
    
    # Verify directory was created
    assert os.path.exists(TEST_OUTPUT_DIR), "Target directory should be created"
    