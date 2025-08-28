import tempfile
import os
import csv
from anonymize_roster import read_roster_file, create_anonymized_roster


def test_read_roster_file():
    content = [
        {"First Name": "Alice", "Last Name": "Smith", "SID": "123", "Role": "Student"},
        {"First Name": "Bob", "Last Name": "Jones", "SID": "456", "Role": "Student"},
        {"First Name": "Charlie", "Last Name": "Wu", "SID": "", "Role": "Student"}  # Invalid
    ]

    with tempfile.NamedTemporaryFile(mode="w", newline="", delete=False, suffix=".csv") as f:
        writer = csv.DictWriter(f, fieldnames=["First Name", "Last Name", "SID", "Role"])
        writer.writeheader()
        writer.writerows(content)
        file_path = f.name

    try:
        student_ids, roles = read_roster_file(file_path)
        assert len(student_ids) == 2
        assert "Alice_Smith_123" in student_ids
        assert "Bob_Jones_456" in student_ids
        assert "Charlie_Wu_" not in student_ids
        assert roles["Alice_Smith_123"] == "Student"
    finally:
        os.remove(file_path)

'''
def test_create_anonymized_roster(tmp_path):
    # Input data
    mapping = {
        "Alice_Smith_123": "anon001",
        "Bob_Jones_456": "anon002"
    }
    roles = {
        "Alice_Smith_123": "Student",
        "Bob_Jones_456": "TA"
    }

    output_path = tmp_path / "anon_roster.csv"
    create_anonymized_roster(mapping, roles, str(output_path))

    # Read the output file and check correctness
    with open(output_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
    for row in rows:
        assert row["SID"] in {"anon001", "anon002"}
        assert row["Full Name"] == row["SID"]
        assert row["Email"] == f"{row['SID']}@example.edu"
        assert row["Role"] in {"Student", "TA"}
'''