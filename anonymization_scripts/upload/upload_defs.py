from bs4 import BeautifulSoup
import os
import re
import time
import json
import shutil
import zipfile
import tempfile
import platform

import mainScript as main

if platform.system() == "Windows":
    import gui_win as gui
else:
    #macOS
    import gui_macOS as gui


def extract_name_from_filename(filename):
    """
    Extract student name from filename
    
    Args:
        filename (str): Filename, assumed format "FirstName_LastName_ID.zip"
        
    Returns:
        str: Student name
    """
    base_name = os.path.splitext(os.path.basename(filename))[0]
    return base_name


def extract_zip_to_temp(zip_path):
    """
    Extract ZIP file to temporary directory and return file list
    
    Args:
        zip_path (str): ZIP file path
        
    Returns:
        tuple: (temp directory path, extracted files list[(file_path, relative_path)])
    """

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Created temp directory: {temp_dir}")

    extracted_files = []

    try:
        # Extract ZIP file to temporary directory
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            print(f"Extracted {os.path.basename(zip_path)} to temp directory\n")

        # Get list of extracted files
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, temp_dir)
                extracted_files.append((file_path, rel_path))

        print(f"✅ Found {len(extracted_files)} files:")
        for _, rel_path in extracted_files:
            print(f"  - {rel_path}")

    except Exception as e:
        print(f"Error extracting file: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return temp_dir, extracted_files


def get_upload_form_data(session, upload_url, student_name):
    """
    Get upload form data and find student ID
    
    Args:
        session: Logged-in session object
        upload_url (str): Upload page URL
        student_name (str): Student name
        
    Returns:
        tuple: (CSRF token, student ID or None)
    """

    # Get upload page and analyze structure
    upload_page = session.get(upload_url)
    soup = BeautifulSoup(upload_page.text, 'html.parser')

    # Verify login status
    if "Log Out" not in upload_page.text:
        print("⚠️ Session may be expired, trying to re-authenticate...")
        return None, None

    # Try to get the correct csrf token
    csrf_meta = soup.find('meta', {'name': 'csrf-token'})

    if csrf_meta and 'content' in csrf_meta.attrs:
        csrf_token = csrf_meta['content']
        print('\n✅ Found token in meta')
        # print(csrf_token)
    else:
        # If not found in meta, try to find in input tag
        csrf_input = soup.find('input', {'name': 'authenticity_token'})
        if csrf_input and 'value' in csrf_input.attrs:
            csrf_token = csrf_input['value']
            print('\n✅ Found token in input')
            # print(csrf_token)
        else:
            print('⚠️ CSRF token not found')
            return None, None
        
    # Find student data
    student_data = None
    roster_pattern = re.compile(r'gon\.roster\s*=\s*(\[.*?\]);', re.DOTALL)
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'gon.roster' in script.string:
            matches = roster_pattern.search(script.string)
            if matches:
                try:
                    student_json = matches.group(1)
                    student_data = json.loads(student_json)
                    #print(f"Successfully extracted student data: {len(student_data)} students")
                except json.JSONDecodeError:
                    print("Failed to parse student data JSON")
                    continue
    # Extract student ID from HTML
    target_student_id = None
    if student_data and student_name:
        for student in student_data:
            if student_name.lower() in student.get('name', '').lower():
                target_student_id = student.get('id')
                print(f"\n✅ Found matching student ID: {target_student_id} for {student.get('name')}")
                break

        if target_student_id is None:
            print(f"⚠️ Warning: Could not find ID for student '{student_name}'")
            # Save student list for debugging
            debug_dir = "gradescope_debug"
            os.makedirs(debug_dir, exist_ok=True)
            with open(os.path.join(debug_dir, f"roster_dump_{int(time.time())}.json"), "w", encoding="utf-8") as f:
                json.dump(student_data, f, indent=2)
            print(f"Saved student data for debugging")

    return csrf_token, target_student_id


def prepare_file_uploads(extracted_files):
    """
    Prepare file upload list
    
    Args:
        extracted_files (list): List of extracted files [(file_path, relative_path)]
        
    Returns:
        tuple: (files list, file_objects list)
    """
    files = []
    file_objects = []  # Store file objects to close later

    for i, (file_path, rel_path) in enumerate(extracted_files):
        rel_path = rel_path.replace('\\', '/')
        print(f"Adding file {i + 1}/{len(extracted_files)}: {rel_path}")

        # 打开文件
        file_obj = open(file_path, 'rb')
        file_objects.append(file_obj)

        # Add to files list, using tuple format (key name, (filename, file object, content type))
        files.append(('submission[files][]', (rel_path, file_obj, 'application/octet-stream')))

        # Simulate user file selection delay
        time.sleep(0.1)

    return files, file_objects


def upload_files(session, upload_url, csrf_token, student_id, files):
    """
    Upload files to Gradescope
    
    Args:
        session: Logged-in session object
        upload_url (str): Upload page URL
        csrf_token (str): CSRF token
        student_id (str or None): Student ID
        files (list): Prepared files list
        
    Returns:
        requests.Response: Upload response object
    """

    # Prepare base form data
    data = {
        'utf8': '✓',
        'authenticity_token': csrf_token,
        'submission_method': 'upload',
    }

    # Add student ID
    if student_id:
        data['submission[owner_id]'] = str(student_id)
        print(f"Setting submission student ID: {student_id}")

    # Send upload request
    print("\n--- Sending upload request ---")
    print(f"Uploading {len(files)} files...")

    upload_resp = session.post(
        upload_url,
        data=data,
        files=files,  # Tuple list format
        allow_redirects=True
    )

    print(f"Response status code: {upload_resp.status_code}")
    return upload_resp


def verify_upload(session, course_id, assignment_id, upload_resp, student_name, debug_dir):
    """
    Verify if upload was successful
    
    Args:
        session: Logged-in session object
        course_id (str): Course ID
        assignment_id (str): Assignment ID
        upload_resp (requests.Response): Upload response object
        student_name (str): Student name
        debug_dir (str): Debug directory path
        
    Returns:
        bool: Whether upload was successful
    """
    os.makedirs(debug_dir, exist_ok=True)
    success = False

    # Create timestamped filename to avoid overwriting
    timestamp = int(time.time())

    # Save response content for analysis
    resp_filename = f"upload_response_{timestamp}.html"
    with open(os.path.join(debug_dir, resp_filename), "w", encoding="utf-8") as f:
        f.write(upload_resp.text)
    print(f"Saved response content to debug directory: {resp_filename}")

    if upload_resp.status_code == 200 or upload_resp.status_code == 302:
        print(f"✅ File uploading should be successful.")
        # Check if there's a redirect URL
        if 'Location' in upload_resp.headers:
            redirect_url = upload_resp.headers['Location']
            print(f"Redirecting to:{redirect_url}")

            # Visit redirect URL to confirm submission
            if not redirect_url.startswith('http'):
                redirect_url = f"https://www.gradescope.com{redirect_url}"
            confirm_resp = session.get(redirect_url)
            print(f"Confirmation page status code: {confirm_resp.status_code}")

        # Check submissions list page to confirm upload success
        submissions_list_url = f"https://www.gradescope.com/courses/{course_id}/assignments/{assignment_id}/submissions"
        submissions_resp = session.get(submissions_list_url)

        list_filename = f"submissions_list_{timestamp}.html"
        with open(os.path.join(debug_dir, list_filename), "w", encoding="utf-8") as f:
            f.write(submissions_resp.text)
        print(f"Saved submissions list page to debug directory: {list_filename}")

        # Two verification methods:
        # 1. Check if student name exists in submissions list
        if student_name and student_name.lower() in submissions_resp.text.lower():
            print(f"✅ Confirmed: Found student {student_name} in submissions list")
            success = True
        # 2. Check if page has successful submission indication
        elif "Your submission was received" in upload_resp.text or "successfully uploaded" in upload_resp.text:
            print(f"✅ Confirmed: Upload response indicates successful submission")
            success = True
        else:
            print(f"⚠️ Warning: Student {student_name} not found in submissions list")
    else:
        print(f"⚠️ File upload failed. Status code: {upload_resp.status_code}")
        error_filename = f"error_response_{timestamp}.html"
        with open(os.path.join(debug_dir, error_filename), "w", encoding="utf-8") as f:
            f.write(upload_resp.text)
        print(f"Saved error response content to debug directory: {error_filename}")

    return success


def cleanup_temp_dir(temp_dir):
    """
    Clean up temporary directory and save important debug files
    
    Args:
        temp_dir (str): Temporary directory path
        debug_dir (str): Debug directory path
    """
    try:
        # Clean up temporary directory
        #print(f"\nCleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Temporary directory cleaned up")

    except Exception as e:
        print(f"\nError cleaning up temporary directory: {e}")
        print("Please delete the temporary directory manually")


def upload_single_assignment(session, course_id, assignment_id, zip_path):
    """
    Upload a single assignment file to Gradescope
    
    Args:
        session: Logged-in session object
        course_id (str): Course ID
        assignment_id (str): Assignment ID
        zip_path (str): ZIP file path
        
    Returns:
        bool: Whether upload was successful
    """
    debug_dir = main.get_output_path("gradescope_debug")
    os.makedirs(debug_dir, exist_ok=True)
    success = False

    # Check if file exists
    if not os.path.exists(zip_path):
        print(f"⚠️ {os.path.basename(zip_path)} does not exist. Cannot upload.")
        return False

    # Extract student name from filename
    student_name = extract_name_from_filename(os.path.basename(zip_path))
    print(f"Extracted student name: {student_name}")

    temp_dir = None
    file_objects = []

    try:
        print(f"Processing file: {os.path.basename(zip_path)}")

        # Upload URL
        upload_url = f'https://www.gradescope.com/courses/{course_id}/assignments/{assignment_id}/submissions'
        
        # Extract ZIP to temporary directory
        temp_dir, extracted_files = extract_zip_to_temp(zip_path)

        # Get upload form data and student ID
        csrf_token, student_id = get_upload_form_data(session, upload_url, student_name)

        if csrf_token is None:
            print("Could not get CSRF token, session may have expired")
            return False
        
        # Prepare file upload
        files, file_objects = prepare_file_uploads(extracted_files)

        # Upload files
        upload_resp = upload_files(session, upload_url, csrf_token, student_id, files)

        # Verify upload
        success = verify_upload(session, course_id, assignment_id, upload_resp, student_name, debug_dir)

    except Exception as e:
        print(f"Error during upload: {e}")
    finally:
        # Close all open files
        for file_obj in file_objects:
            file_obj.close()
        print("All files closed")

        # Clean up temporary directory
        if temp_dir:
            cleanup_temp_dir(temp_dir)
    return success


def upload_mutliple_assignments(session, course_id, assignment_id, files, download_name = "None", upload_name = "None"):
    """ 
    Upload multiple assignment files to Gradescope, using a brand new session for each file 
    
    Args: 
        session: 
        course_id: course ID 
        assignment_id: assignment ID 
        zip_files: ZIP files Path list 
    
    Returns: 
        list: list of uploaded results 
    """

    results = []
    debug_dir = main.get_output_path("gradescope_debug")
    for i, zip_path in enumerate(files):
        print(f'\n=== [{i+1}/{len(files)}] Handle file: {os.path.basename(zip_path)} ===')
        try:
            # Wait a while to avoid too frequent requests
            time.sleep(1)
            
            # Uploading a single file
            success = upload_single_assignment(session, course_id, assignment_id, zip_path)

            # Recording results
            status = "✅ Success" if success else "⚠️ Failed"
            results.append((os.path.basename(zip_path), success, status))
            
            
        except Exception as e:
            print(f"Error while processing file: {e}")
            import traceback
            traceback.print_exc()
            results.append((os.path.basename(zip_path), False, f"Error: {str(e)}"))
            
        finally:
            # Wait a while to avoid too frequent requests
            time.sleep(1)
        time.sleep(0.1)

    # print results
    summary = f"Anonymize:\n\n{download_name}\n\nUploaded submission to:\n\n{upload_name}:\n\n"
    for filename, success, status in results:
        summary += f"\n{filename}: {status}"
    
    gui.gui_show_selection(summary, "Upload results summary")
    
    success_count = sum(1 for _, success, _ in results if success)
    cleanup_temp_dir(debug_dir)
    print(f"Total {len(results)} files uploaded, {success_count} successfully, success Rate: {success_count/len(results)*100:.1f}%\n")
    return results

