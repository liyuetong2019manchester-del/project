"""
anonymize_roster Module - Handling the anonymization of student rosters 

This module is used to: 
1. Read the original roster CSV file 
2. Apply the anonymization 
3. Generate a new roster file containing only the anonymous IDs and roles 
"""

import csv
import os
import random


def read_roster_file(file_path, name_student_ids = list(), roles = dict()):
    """ 
    Read roster CSV file to extract student IDs and roles 
    
    Parameters: 
        file_path (str): path to roster file 
        
    Returns: 
        tuple: tuple containing: 
        - list: list of student IDs 
        - dict: mapping of student IDs to roles 
    """
    check_diff = list()
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            first_name = row.get('First Name', '').strip()
            last_name = row.get('Last Name', '').strip()
            full_name = row.get('Name', '').strip()
            student_id = row.get('SID', '').strip()
            role = row.get('Role', '').strip()

            if not student_id:
                continue
            
            if full_name:
                first_name, last_name = full_name.split()

            name_student_id = f"{first_name}_{last_name}_{student_id}"

            diff = f"{last_name}_{student_id}"

            if name_student_id in name_student_ids:
                #print(f'detected {name_student_id}, pass this student.')
                continue
            #print(name_student_id)
            name_student_ids.append(name_student_id)
            roles[name_student_id] = role
            check_diff.append(diff)

    if not name_student_ids or not roles:
        return False
    
    return name_student_ids, roles, check_diff
    

def create_anonymized_roster(mapping, roles, saved_path):
    """
     Create anonymized roster file containing only anonymous IDs and roles 
    
    Parameters: 
        mapping (dict): mapping of name_student_id to anonymous IDs 
        roles (dict): mapping of name_student_id to student roles 
        saved_path (str): path to output file 
    """

    # make sure the output directory exists
    output_dir = os.path.dirname(saved_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mapping_items = list(mapping.items())
    random.shuffle(mapping_items)

    rows = []
    for name_student_id, anonymous_id in mapping_items:
        # get a stable number name
        name = int(anonymous_id, 16) % 1000
        rows.append({
            'First Name': f"st{name}",
            'Last Name': anonymous_id,
            'SID': anonymous_id,
            'Email': f"{anonymous_id}@example.edu",
            'Role': roles[name_student_id]
        })
    random.shuffle(rows)

    # write anonymized roster file
    with open(saved_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['First Name', 'Last Name', 'SID', 'Email', 'Role']
        writer = csv.DictWriter(f, fieldnames = fieldnames)
        writer.writeheader()
        
        for row in rows:
            writer.writerow(row)
    
    print(f"Anonymized rosters have been saved to {saved_path}.")
