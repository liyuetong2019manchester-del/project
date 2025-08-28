""" 
anonymization_sub Module - Anonymize the assignment files submitted by students 

This module contains: 
    1. anonymize the assignment files submitted by students 
    2. change the file name from firstname_lastname_studentid.zip format to anonymous ID.zip 
    3. use a temporary mapping table that is deleted after processing is complete 
"""

import os
import re
import shutil


def find_submission_files(submission_dir, pattern=r'.*\.zip'):
    """
    Finds files in submission directory that match pattern 
    
    Parameters: 
    submission_dir (str): submission directory 
    pattern (str): regular expression for filename pattern 
        
     Returns: 
    list: list of paths to files found 
    """
    matching_files = []
    
    for root, _, files in os.walk(submission_dir):
        for filename in files:
            if re.match(pattern, filename, re.IGNORECASE):
                matching_files.append(os.path.join(root, filename))
    
    return matching_files


def extract_student_identifier(filename, name_student_ids):
    """
    Extracts student identifier from filename 
    
    Parameters: 
        filename (str): filename 
        name_student_ids: all student ids
        
    Returns: 
        str: name_student_ids extracted, returns None if not found 
    """
    # Trying to extract firstname_lastname_number format
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    # Try to extract the name part (the first two parts of the filename, e.g. Ana_Ana)
    parts = base_name.split('_')
    if len(parts) >= 2:
        # Take the first two parts as the name
        name_part = f"{parts[0]}_{parts[1]}"
        
        # Find matching name_student_ids in student_ids
        for full_id in name_student_ids:
            # Check if it starts with name_part
            if full_id.lower().startswith(name_part.lower() + "_"):
                return full_id
    
    return None


def anonymize_submission_files(submission_dir, output_dir, mapping, student_ids):
    """
    Anonymize submission files, changing filenames from firstname_lastname.zip to anonymousID.zip
    
    Args:
        submission_dir (str): Directory containing submission files
        output_dir (str): Output directory for anonymized files
        mapping (dict): Mapping from student identifiers (firstname_lastname_studentid) to anonymous IDs
        student_ids (list): List of complete student identifiers
        
    Returns:
        tuple: (number of processed files, number of successfully anonymized files)
    """
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find all submission files
    submission_files = find_submission_files(submission_dir)
    
    if not submission_files:
        print(f"Warning: No submission files found in {submission_dir}")
        return 0, 0
    
    processed_count = 0
    anonymized_count = 0
    
    print('')

    # Process each file
    for file_path in submission_files:
        processed_count += 1
        file_name = os.path.basename(file_path)
        
        # Match complete student identifier (firstname_lastname_studentid) from filename (firstname_lastname.zip)
        full_student_id = extract_student_identifier(file_name, student_ids)
        
        if full_student_id and full_student_id in mapping:
            # Create new filename using anonymous ID
            anonymous_id = mapping[full_student_id]
            file_ext = os.path.splitext(file_name)[1]
            new_file_name = f"{anonymous_id}{file_ext}"
            new_file_path = os.path.join(output_dir, new_file_name)
            
            # Copy and rename file
            shutil.copy2(file_path, new_file_path)
            anonymized_count += 1
            print(f"Anonymized: {new_file_name}")
            
        else:
            # Unable to match student identifier
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            print(f"Warning: Could not match '{base_name}' to any complete student identifier")
    
    print(f"Anonymized submission files saved to: {output_dir}")
    return processed_count, anonymized_count

