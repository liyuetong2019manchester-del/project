from bs4 import BeautifulSoup
import os
import re
import csv
import time


def setup_directories(base_dirs):
    """
    Create necessary directory structure
    
    Args:
        base_dirs (dict): Contains various required directory paths
        
    Returns:
        dict: Contains directory and CSV file paths
    """
    # Create folders (if they don't exist)
    for dir_path in base_dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    # Define CSV file paths
    csv_paths = {
        'zip': os.path.join(base_dirs['zip'], 'raw_zip_index.csv'),
        'pdf': os.path.join(base_dirs['pdf'], 'graded_copy_index.csv')
    }

    return csv_paths


def get_submissions(session, course_id, assignment_id):
    """
    Get list of all student submissions
    
    Args:
        session: Logged-in session object
        course_id (str): Course ID
        assignment_id (str): Assignment ID
        
    Returns:
        list: List of (student_name, submission_id) tuples
    """
    assignment_url = f'https://www.gradescope.com/courses/{course_id}/assignments/{assignment_id}/submissions'
    resp = session.get(assignment_url)
    soup = BeautifulSoup(resp.text, 'html.parser')

    submissions = []
    for row in soup.find_all('tr'):
        a_tag = row.find('a', href=True)
        if a_tag and '/submissions/' in a_tag['href']:
            name = a_tag.text.strip()
            match = re.search(r'/submissions/(\d+)', a_tag['href'])
            if match:
                submission_id = match.group(1)
                submissions.append((name, submission_id))

    print(f"🎯 Found {len(submissions)} submissions, starting batch download...")
    return submissions


def download_zip_files(session, course_id, assignment_id, submissions, zip_dir, csv_path):
    """
    Download all student ZIP submissions
    
    Args:
        session: Logged-in session object
        course_id (str): Course ID
        assignment_id (str): Assignment ID
        submissions (list): List of (student_name, submission_id) tuples
        zip_dir (str): Directory path to save ZIP files
        csv_path (str): File path to save CSV index
    """
    print("\n📦 Downloading original submission files (ZIP)...")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['student_name', 'submission_id', 'filename'])
        
        count = 1
        for student_name, submission_id in submissions:
            safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', student_name)
            filename = f"{safe_name}_{submission_id}.zip"
            file_path = os.path.join(zip_dir, filename)

            # Overwrite existing files
            print(f"✅ Downloading: No.{count}")

            zip_url = f"https://www.gradescope.com/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}.zip"
            response = session.get(zip_url)

            if response.status_code == 200 and response.content.startswith(b'PK'):
                with open(file_path, 'wb') as zf:
                    zf.write(response.content)
                writer.writerow([student_name, submission_id, filename])
            else:
                print(f"⚠️ ZIP download failed for No.{count}, skipping")

            time.sleep(1)
            count += 1
    #print(f"📂 ZIP files saved in: {zip_dir}")


def download_pdf_files(session, course_id, assignment_id, submissions, pdf_dir, csv_path):
    """
    Download all graded PDF files for students
    
    Args:
        session: Logged-in session object
        course_id (str): Course ID
        assignment_id (str): Assignment ID
        submissions (list): List of (student_name, submission_id) tuples
        pdf_dir (str): Directory path to save PDF files
        csv_path (str): File path to save CSV index
    """
    print("\n📄 Downloading Graded Copy PDFs...")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['student_name', 'submission_id', 'filename'])

        for student_name, submission_id in submissions:
            safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', student_name)
            filename = f"{safe_name}_{submission_id}.pdf"
            file_path = os.path.join(pdf_dir, filename)

            # Overwrite existing files
            print(f"✅ Downloading: {filename}")

            pdf_url = f"https://www.gradescope.com/courses/{course_id}/assignments/{assignment_id}/submissions/{submission_id}.pdf"
            response = session.get(pdf_url)

            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                with open(file_path, 'wb') as pf:
                    pf.write(response.content)
                writer.writerow([student_name, submission_id, filename])
            else:
                print(f"⚠️ PDF does not exist or not graded for {student_name}, skipping")
            time.sleep(1)
    #print(f"📂 PDF files saved in: {pdf_dir}")


def download_roster(session, course_id, roster_path):
    """
    Download course roster CSV file
    
    Args:
        session: Logged-in session object
        course_id (str): Course ID
        roster_path (str): File path to save roster
    """
    roster_url = f"https://www.gradescope.com/courses/{course_id}/memberships.csv"

    # Overwrite existing file
    print("\n📜 Downloading Roster CSV file...")
    response = session.get(roster_url)

    if response.status_code == 200:
        with open(roster_path, 'wb') as f:
            f.write(response.content)
        print(f"📂 Roster file saved")
    else:
        print(f"⚠️ Roster download failed")

