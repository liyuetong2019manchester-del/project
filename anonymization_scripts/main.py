import platform

import mainScript as m

if platform.system() == "Windows":
    import gui_win as gui
else:
    #macOS
    import gui_macOS as gui


def main():
    '''
    Main function
    '''
    # Using dialog box to get login information
    print("Welcome to Gradescope Anonymizer")
    email = gui.gui_input("Enter email to login: ")
    password = gui.gui_password_input("Enter password: ")
        
    session = m.login(email, password)
        
    anon_path = m.get_hidden_data_path()
    roster_base_dir = f'{anon_path}/gradescope_roster'
        
    download_course_ids_names = m.choose_courses(session, "Please choose the courses you want to anonymize:")
        

    if len(download_course_ids_names) == 0:
        print('Please choose at least one course')
        download_course_ids_names = m.choose_courses(session, "Please choose the courses you want to anonymize:")
        if len(download_course_ids_names) == 0:
            print("No courses selected, program exiting.")
            return
    download_course_names = ""
    for k, v in download_course_ids_names.items():
        download_course_names += f"{v}\n"

    m.anonymize_course(session, download_course_ids_names, roster_base_dir, anon_path)
    gui.gui_show_selection(f"Courses anonymized successfully: \n{download_course_names}", "Success")

    m.cleanup_folder()

if __name__ == "__main__":
    main()