"""
anonymization_core Module - Provides all basic anonymization functionality 

This module contains: 
    1. Functions for generating anonymous IDs 
    2. Functions for creating and managing mappings from student IDs to anonymous IDs 
    3. Functions for saveing, loading and deleting mapping tables 
"""

import hashlib
import os
import json

DEFAULT_SALT = 'gradescope_anonmization'


def generate_anonymous_id(name_student_id, salt = DEFAULT_SALT):
    """
    Generates a unique anonymous ID for a student using SHA-256 hashing.
    
    Parameters:
        name_student_id (str): The original student ID to be anonymized
        salt (str): A random string added to increase security of the hash
        
    Returns:
        str: An 8-character anonymous ID derived from the hashed student ID
             This ID will be consistent for the same name_student_id and salt
    """
    # Create the hash value with using student ID and a salt value
    hash_obj = hashlib.sha256((name_student_id + salt).encode())
    hashed = hash_obj.hexdigest()

    # Use the first 8 bits of the hash as an anonymous ID
    return hashed[:8]


def create_anonymization_mapping(name_student_ids, id_to_anonymous = dict(), salt = DEFAULT_SALT):
    """
    Creates a mapping table between student IDs and their anonymous IDs.
    
    This function creates a unique anonymous number for each student ID in the list. 
    If there are duplicate anonymous IDs, it adds the number to the student ID 
    and recalculates the hash, which ensures that each anonymous ID is unique.
    
    Parameters:
        name_student_ids: List of student IDs to anonymize
        salt (str): Salt value to use for hashing. If None, a random salt is generated.
        
    Returns:
        dict: Mapping from student IDs to anonymous IDs
    """
    # Create mapping tables
    duplicate_anonymous_ids = set()

    # Create an anonymous ID for each student ID
    for name_student_id in name_student_ids:
        if name_student_id in id_to_anonymous:
            continue
        anonymous_id = generate_anonymous_id(name_student_id, salt)
        duplicate_anonymous_ids.add(anonymous_id)

        # save the mapping data
        id_to_anonymous[name_student_id] = anonymous_id

    return id_to_anonymous


def save_mapping_table(id_to_anonymous, saved_path = 'mapping_table.json'):
    """
    Saves the student ID to anonymous ID mapping table to a file.
    
    This function takes the mapping dictionary, creates a bidirectional 
    mapping structure, and save it.
    
    Parameters:
        mapping: Dictionary mapping student IDs to anonymous IDs
        saved_path: File path to save the mapping table. 
                   Defaults to 'mapping_table.json'
    
    Returns:
       Bool: Whether the saving is successful or not.
    """
    # Create reverse mapping
    anonymous_to_id = {anonymous_id: name_student_id for name_student_id, anonymous_id in id_to_anonymous.items()}

    # Data structures to be preserved
    mapping_data = {
        "salt": DEFAULT_SALT,
        "id_to_anonymous": id_to_anonymous,
        "anonymous_to_id": anonymous_to_id
    }

    # Save to file
    with open(saved_path, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, indent=2)

    #print(f"Encrypted mapping table have saved to {saved_path}")
    return True


def load_mapping_table(saved_path = 'mapping_table.json'):
    """
    Loads the mapping table from an encrypted file.
    
    Parameters:
        saved_path: Path to the encrypted mapping table file
        
    Returns:
        tuple: A tuple containing:
            - dict: Mapping from student IDs to anonymous IDs
            - dict: Mapping from anonymous IDs to student IDs
    """
    # Read the encrypted file
    with open(saved_path, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    
    # Extract the mapping tables and salt
    id_to_anonymous = mapping_data.get("id_to_anonymous", {})
    anonymous_to_id = mapping_data.get("anonymous_to_id", {})
    
    return id_to_anonymous, anonymous_to_id


def delete_mapping_table(saved_path = 'mapping_table.json'):
    """
    Delete the mapping table file 
    
    Parameters: 
        saved_path: path of the mapping table file to be deleted, default is 'mapping_table.json' 
        
    Returns: 
        bool: Whether the deletion is successful or not.
    """
    if os.path.exists(saved_path):
        os.remove(saved_path)
        print(f"Delete mapping table successfully: {saved_path}")
        return True
    else:
        print(f"No such file found: {saved_path}")
        return False
    
