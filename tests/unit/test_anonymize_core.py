import pytest
import sys
import os
import json

# Add module path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../anonymization_scripts/anonymization')))
from anonymize_core import generate_anonymous_id, create_anonymization_mapping, save_mapping_table, load_mapping_table, delete_mapping_table  # type: ignore

# Fixed path for test file
TEST_FILE = "test_mapping_table.json"

# Setup and cleanup before and after each test
@pytest.fixture
def mapping_table():
    """Provide test mapping table"""
    test_mapping = {
        "student1": "anon1234",
        "student2": "anon5678"
    }
    yield test_mapping
    
    # Cleanup
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

# Consistency test
def test_generate_anonymous_id_consistency():
    """Test the consistency of anonymous ID generation"""
    student_id = "student123"
    salt = "somesalt"
    id1 = generate_anonymous_id(student_id, salt)
    id2 = generate_anonymous_id(student_id, salt)
    assert id1 == id2, "Same input should return the same anonymous ID"

# Length test
def test_generate_anonymous_id_length():
    """Test the length of generated anonymous ID"""
    student_id = "student456"
    salt = "othersalt"
    anon_id = generate_anonymous_id(student_id, salt)
    assert len(anon_id) == 8, "Anonymous ID should be 8 characters long"

# Unique ID test
def test_create_anonymization_mapping_unique_ids():
    """Test that the created anonymization mapping contains unique IDs"""
    student_ids = ["student1", "student2", "student3"]
    mapping = create_anonymization_mapping(student_ids)
    anon_ids = list(mapping.values())
    assert len(anon_ids) == len(set(anon_ids)), "Each student ID should have a unique anonymous ID"
'''
# Anonymization mapping test
def test_create_anonymization_mapping_correct_mapping():
    """Test the correctness of anonymization mapping"""
    student_ids = ["student1", "student2"]
    salt = "customsalt"
    mapping = create_anonymization_mapping(student_ids, salt)
    for student_id in student_ids:
        expected_anon_id = generate_anonymous_id(student_id, salt)
        assert mapping[student_id] == expected_anon_id, f"Anonymous ID mapping for student ID {student_id} is incorrect"
'''
# Save mapping table test
def test_save_mapping_table(mapping_table):
    """Test if mapping table is correctly saved to file"""
    result = save_mapping_table(mapping_table, TEST_FILE)
    assert result is True, "Failed to save mapping table"
    assert os.path.exists(TEST_FILE), "Mapping table file was not created"

    # Verify file content
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert "id_to_anonymous" in data, "Saved file is missing id_to_anonymous key"
    assert "anonymous_to_id" in data, "Saved file is missing anonymous_to_id key"
    assert data["id_to_anonymous"] == mapping_table, "Saved mapping table content is incorrect"

# Load mapping table test
def test_load_mapping_table(mapping_table):
    """Test if mapping table is correctly loaded"""
    # First save the mapping table
    save_mapping_table(mapping_table, TEST_FILE)

    # Load mapping table
    id_to_anonymous, anonymous_to_id = load_mapping_table(TEST_FILE)
    assert id_to_anonymous == mapping_table, "Loaded id_to_anonymous mapping is incorrect"
    expected_reverse_mapping = {v: k for k, v in mapping_table.items()}
    assert anonymous_to_id == expected_reverse_mapping, "Loaded anonymous_to_id mapping is incorrect"

# Delete mapping table test
def test_delete_mapping_table(mapping_table):
    """Test if mapping table file is correctly deleted"""
    # First save the mapping table
    save_mapping_table(mapping_table, TEST_FILE)

    # Delete mapping table file
    result = delete_mapping_table(TEST_FILE)
    assert result is True, "Failed to delete mapping table file"
    assert not os.path.exists(TEST_FILE), "Mapping table file was not deleted"

    # Test deleting non-existent file
    result = delete_mapping_table(TEST_FILE)
    assert result is False, "Deleting non-existent file should return False"