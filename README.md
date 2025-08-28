# Gradescope Submission Anonymizer

An application for anonymizing student submissions in Gradescope to facilitate fair and unbiased grading.
## GitHub Account Mapping

Due to Uni account restrictions, some team members have used personal GitHub accounts to contribute to this repository. Below is a mapping of GitHub usernames to student IDs for clarification:

- GitHub account `1999051` corresponds to student ID `a1910537`
- GitHub account `LEe5512` corresponds to student ID `a1898722`

This mapping is provided to ensure accurate attribution of contributions.

## 🔀 Repository Branch Structure

Our repository follows a simple and clear branching strategy to support both stable development and collaborative testing.

### 🌟 `main` Branch
- **Purpose**: This is the **production branch** used to store finalized and reviewed code.
- **Contents**:
  - Fully functional and stable features
  - Updated documentation
  - Code ready for deployment or integration
- **Access**: Restricted to maintainers or through pull requests with approval

### 🧪 `Testing` Branch
- **Purpose**: This is the **testing branch** for internal QA, bug fixes, and trial implementations.
- **Contents**:
  - Experimental or work-in-progress features
  - Test cases, debugging logs, and temporary tools
- **Access**: Open to testers and developers

> 🔧 Tip: Always sync your feature branches with `test`, and only promote to `main` after successful reviews and test case validations.

---

## 📋 Installation Guide

### Windows Installation
1. Download the latest Windows release from the Releases section
2. Extract the ZIP file to your preferred location
3. Run the `anonymize_courses_Win.exe` file

### macOS Installation
1. Download the latest macOS release from the Releases section
2. Open the DMG file and drag the application to your Applications folder
3. Open the application from your Applications folder
   - Note: You may need to allow the application in System Preferences > Security & Privacy if you receive a security warning

---

## 🚀 Using the Anonymizer

### Before You Begin: Pre-requisites Checklist

Before running the application, please ensure you have:

1. ✅ Instructor or TA access to the source Gradescope course containing the submissions you want to anonymize
2. ✅ Created a new destination course and assignment in Gradescope where the anonymized submissions will be placed
3. ✅ Gradescope login credentials (email and password)


### Step-by-Step Usage Guide

1. Launch the application (GUI interface will appear)
2. Enter your Gradescope email and password when prompted
3. Choose the courses and assignments you want to anonymize (the course containing the submissions you want to anonymize)
4. Choose the destination Course and Assignment (the new course where anonymized submissions will be placed)
5. While running, the program will ask you to upload the roster of source course to the destination course(remember to switch the name pattern from full name to first name and last name), press next step when you have done that.
6. Wait for the process to complete - the application will:
   - Download all submissions from the source assignment
   - Remove identifying information from the submissions
   - Upload the anonymized submissions to the destination assignment
7. When the process is complete, the application will display a success message and automatically exit

## 🔍 Troubleshooting

### Common Issues

- **Login Failed**: Verify your Gradescope credentials and ensure you have the correct access permissions
- **Invalid Course/Assignment ID**: Double-check the IDs from the Gradescope URLs
- **Permission Denied**: Ensure you have instructor or TA access to both source and destination courses

## 📝 Notes for Instructors

- The anonymization process preserves all submission content but removes student names, IDs, and other identifying information
- Grading can proceed normally in the destination course
- For optimal performance, run the application when network traffic to Gradescope is lower (typically late evening or early morning)

---

© 2025 Gradescope Anonymizer Team | Licensed under MIT
