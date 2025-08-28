import os
import sys
import time
import shutil
import platform
from pathlib import Path


import anonymization.anonymize_core as core
import anonymization.anonymize_roster as roster
import anonymization.anonymize_sub as sub
import download.download_defs as down
import upload.upload_defs as up
import gradescope.gradescope_api as api

if platform.system() == "Windows":
    import gui_win as gui
else:
    #macOS
    import gui_macOS as gui


TEMP_PATHS = list()


def get_program_dir() -> str:
    """
     Returns the directory where the program is currently running (dist/anon when packaged; the .py directory when unpackaged) 
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_output_path(filename: str) -> str:
    """
     Returns the full path to the writable file, located in the anon program run directory 
    """
    return os.path.join(get_program_dir(), filename)


def get_hidden_data_path() -> str:
    system = platform.system()
    timestamp = time.strftime("%Y%m%d")
    if system == "Windows":
        base = os.getenv("APPDATA") or str(Path.home())
        path = Path(base) / f"anon_tool_{timestamp}"
    else:
        # macOS or Linux
        path = Path.home() / f".anon_tool_{timestamp}"

    path.mkdir(parents=True, exist_ok=True)
    TEMP_PATHS.append(str(path))
    return str(path)  # Returns a string for easy use with f-string


def login(email, password):
    session = api.login_to_gradescope(email, password)
    return session


def get_base_dirs(anon_path, download_base_id = None, download_assignment_id = None):
    base_dirs = {
        'zip': f'{anon_path}/gradescope_raw_zips_{download_base_id}_{download_assignment_id}',  # save original ZIP
        'pdf': f'{anon_path}/gradescope_graded_copies_{download_base_id}_{download_assignment_id}',  # save Graded page PDF
    }
    return base_dirs


def cleanup_folder(temp_folders = TEMP_PATHS):
    print("Deleting temp folders!")
    for temp_path in temp_folders:
        time.sleep(0.2)
        try:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
                #print(f"Delete temp folder {temp_path} sucessuflly!")
        except Exception as e:
            print(f"Failed to delete temp folder: {e}")
        

'''
def choose_assignments(session, course_id):
    assignments = api.get_assignment_id(session, course_id)
    
    # display all assignments for user selection
    assignments_names = list(assignments.keys())
    [print(f"{i+1}. {name}") for i, name in enumerate(assignments_names)]
    
    # get user selections
    choices = input('Please select assignments (enter serial number, multiple serial numbers separated by spaces, enter "all" to select all): ').strip()
    
    # init result dict
    result = {}
    
    # processing user selections
    if choices.lower() == 'all':
        # select all assignments, reverse key-value pairs
        for assignment_name, assignment_id in assignments.items():
            result[assignment_id] = assignment_name
    else:
        # select a specific assignment to create a dictionary containing the selected course
        for idx in choices.split():
            if idx.isdigit() and 0 < int(idx) <= len(assignments_names):
                assignment_name = assignments_names[int(idx)-1]
                assignment_id = assignments[assignment_name]
                result[assignment_id] = assignment_name
    
    return result
    
def choose_courses(session):
    courses = api.get_course_id(session)
    
    # display all courses for user selection
    courses_names = list(courses.keys())
    [print(f"{i+1}. {name}") for i, name in enumerate(courses_names)]
    
    # get user selections
    choices = input('Please select courses (enter serial number, multiple serial numbers separated by spaces, enter "all" to select all): ').strip()
    
    # init result dict
    result = {}
    
    # processing user selections
    if choices.lower() == 'all':
        # select all courses, reverse key-value pairs
        for course_name, course_id in courses.items():
            result[course_id] = course_name
    else:
        # select a specific course to create a dictionary containing the selected course
        for idx in choices.split():
            if idx.isdigit() and 0 < int(idx) <= len(courses_names):
                course_name = courses_names[int(idx)-1]
                course_id = courses[course_name]
                result[course_id] = course_name
    
    return result
'''


def choose_courses(session, prompt = "Please select courses"):
    '''
    Select courses
    '''

    courses = api.get_course_id(session)
    courses_names = list(courses.keys())
    
    # use clickable list to select multiple courses
    gui.gui_print("Please select source courses")
    selected_courses = gui.gui_choose_from_list(
        courses_names, 
        prompt, 
        multiple=True, 
        title="Source Course Selection"
    )
    
    # if no course selected
    if not selected_courses:
        return{}
    
    # build result dictionary
    result = {}
    for course_name in selected_courses:
        course_id = courses[course_name]
        result[course_id] = course_name
    
    # display selection summary
    selection_message = "You have selected the following courses:\n\n" + "\n".join(selected_courses)
    if not gui.gui_show_selection(selection_message, "Course Selection Summary"):
        choose_courses(session, "Please select at least one")
    
    return result

def choose_assignments(session, course_id,prompt = "Please select assignments"):
    '''
    Select assignments
    '''

    assignments = api.get_assignment_id(session, course_id)
    assignments_names = list(assignments.keys())
    
    # use clickable list to select assignments
    gui.gui_print("Please select an assignment")
    selected_assignments = gui.gui_choose_from_list(
        assignments_names,
        prompt,
        multiple=True,
        title="Assignment Selection"
    )
    
    # if no assignment selected
    if not selected_assignments:
        return{}
    
    # build result dictionary
    result = {}
    for assignment_name in selected_assignments:
        assignment_id = assignments[assignment_name]
        result[assignment_id] = assignment_name
    
    # display selection summary
    selection_message = f"You have selected the following assignment:\n\n" + "\n".join(selected_assignments)
    if not gui.gui_show_selection(selection_message, "Assignment Selection Summary"):
        choose_assignments(session, course_id, "Please select at least one")
    
    return result


def check_uploaded_roster(session, upload_course_id, roster_base_dir, new_roster_saved_path):
    '''
    Check if there is any different between new roster and exsitng roster
    '''
    roster_path = os.path.join(roster_base_dir, f'gradescope_roster_{upload_course_id}.csv')

    if not gui.gui_show_selection(f"New anonymized roster have been save to:\n{new_roster_saved_path}\n\nUpload it to the new course you want to upload to.\n\nClick 'OK' when you have uploaded.\nClick 'No' to quit the program.", "New Roster uploading..."):
        # if user choose to quit the program, clane the temp folder
        cleanup_folder()
        raise SystemError
    
    down.download_roster(session, upload_course_id, roster_path)

    print("reading existing anonymized roster\n")
    regular_name_student_ids = roster.read_roster_file(roster_path)
    print("reading new anonymized roster\n")
    name_student_ids = roster.read_roster_file(new_roster_saved_path)[2]

    # compare the old and new anonymized roster, to check if there any different between them
    changes = False
    if not regular_name_student_ids:
        changes = True
    else:
        for name_student_id in name_student_ids:
            if name_student_id not in regular_name_student_ids[2]:
                changes = True
    
    # if there is some new student in the new roster, show the messages and recall the fucntion to makre sure user upload the new anonymized roster in the courses
    if changes:
        gui.gui_show_selection("Roster is empty or get new changes in the upload course.\n\nPlease make sure you have uploaded anonymized roster.")
        check_uploaded_roster(session, upload_course_id, roster_base_dir, new_roster_saved_path)


def get_roster(session, roster_base_dir, download_course_ids, upload_course_id, anon_path, upload_to_gradescope):
    '''
    get the combined roster of all choosed courses and anonymize it
    '''
    id_to_anonymous = dict()
    name_student_ids = list()
    roles = dict()

    # read roster of every courses that need to be anonymized, and put the student information together
    for download_course_id in download_course_ids:
        roster_path = os.path.join(roster_base_dir, f'gradescope_roster_{download_course_id}.csv')
        down.download_roster(session, download_course_id, roster_path)

        name_student_ids, roles, check_diff = roster.read_roster_file(roster_path, name_student_ids, roles)
        id_to_anonymous = core.create_anonymization_mapping(name_student_ids, id_to_anonymous)

    # get the mapping table of the combined courses student information
    mapping_table_path = f'{anon_path}/mapping_table.json'
    core.save_mapping_table(id_to_anonymous, mapping_table_path)

    if upload_to_gradescope:
        new_roster_saved_path = get_output_path(f"anonymized_roster_upload_to_{upload_course_id}.csv")
    else:
        new_roster_saved_path = get_output_path(f"anonymized_roster_from_{download_course_ids}.csv")
    roster.create_anonymized_roster(id_to_anonymous, roles, new_roster_saved_path)
    # if user choose to use Gradescope, then check if there is any different between new roster and exsitng roster
    if upload_to_gradescope:
        check_uploaded_roster(session, upload_course_id, roster_base_dir, new_roster_saved_path)
    return name_student_ids, id_to_anonymous


def anonymize_course(session, download_course_ids_names, roster_base_dir, anon_path):
    download_course_ids = list(download_course_ids_names.keys())

    # let user choose if they will upload the anonymized assignment files to Gradescope or not
    upload_to_gradescope = gui.gui_show_selection("If you want to use Gradescope to anonymize the courses, Press 'Yes'.\n\nOtherwise, press 'No' to save the anonymized assignment files to local!", "Upload to Gradescope or Not")
    upload_course_id = ""

    # if user choose to use Gradescope, then get the upload course id
    if upload_to_gradescope:
        upload_course_id_name = choose_courses(session, "Choose the courses you wanna upload to:")
        upload_course_id = list(upload_course_id_name.keys())[0]
    
        if not upload_course_id_name:
            gui.gui_print("No upload course selected. Operation cancelled.")
            return
        
        upload_course_id = list(upload_course_id_name.keys())[0]
    
    # show summary
    summary = "You have selected:\n\n"
    summary += "Download from courses:\n"
    summary += "\n".join([f"- {download_course_ids_names[download_course_id]}" for download_course_id in download_course_ids])
    
    if upload_to_gradescope:
        summary += "\n\nUpload to course:\n"
        summary += f"- {upload_course_id_name[upload_course_id]}"

    if not gui.gui_show_selection(summary, "Selections Summary"):
        gui.gui_print("Operation cancelled by user.")
        return

    os.makedirs(roster_base_dir, exist_ok=True)
    name_student_ids, id_to_anonymous = get_roster(session, roster_base_dir, download_course_ids, upload_course_id, anon_path, upload_to_gradescope)
    
    for download_course_id in download_course_ids:
        prompt = f"Choose the assignments you want to anonymized in {download_course_ids_names[download_course_id]}"
        download_assignment_ids_names = choose_assignments(session, download_course_id, prompt)
        download_assignment_ids = list(download_assignment_ids_names.keys())

        for download_assignment_id in download_assignment_ids:
            # crate path and download assignment files
            base_dirs = get_base_dirs(anon_path, download_course_id, download_assignment_id)
            csv_paths = down.setup_directories(base_dirs)
            submissions = down.get_submissions(session, download_course_id, download_assignment_id)
            down.download_zip_files(session, download_course_id, download_assignment_id, submissions, base_dirs['zip'], csv_paths['zip'])

            # anonymize the downloaded assignemnt files
            if not upload_to_gradescope:
                anonymize_submission_path = get_output_path(f"anonymized_assignments_{download_course_ids_names[download_course_id]}_{download_assignment_ids_names[download_assignment_id]}/")
            else:
                anonymize_submission_path = get_output_path(f"anonymized_submission_{download_course_ids_names[download_course_id]}_{download_assignment_ids_names[download_assignment_id]}/")
            sub.anonymize_submission_files(base_dirs['zip'], anonymize_submission_path, id_to_anonymous, name_student_ids)

            if not upload_to_gradescope:
                gui.gui_show_selection(f"The anonymized files saved in {anonymize_submission_path}", "Anonymized Successfully")
                continue

            TEMP_PATHS.append(anonymize_submission_path)
            # get assignment id will upload to
            upload_assignment_id_name = choose_assignments(session, upload_course_id, 
                                                           f"Anonymizing assignment:\n\n{download_course_ids_names[download_course_id]} - {download_assignment_ids_names[download_assignment_id]}.\n\nSelect which assignment to upload to, only choose one!")
            upload_assignment_id = list(upload_assignment_id_name.keys())[0]

            # Start to upload
            filename = sub.find_submission_files(anonymize_submission_path)
            up.upload_mutliple_assignments(
                session, 
                upload_course_id, upload_assignment_id, filename, 
                f"{download_course_ids_names[download_course_id]} - {download_assignment_ids_names[download_assignment_id]}",
                f"{upload_course_id_name[upload_course_id]} - {upload_assignment_id_name[upload_assignment_id]}"
            )

