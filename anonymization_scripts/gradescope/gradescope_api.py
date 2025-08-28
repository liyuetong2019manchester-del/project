import requests
from bs4 import BeautifulSoup
import random
import uuid
import json
import re

def anti_cache_headers():
    """
    Generate cache-prevention request headers 
    
    Returns: 
        dict: Header with random User-Agent and cache-prevention directive
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0',
        # add random parameters to ensure each request is unique
        'X-Request-ID': str(uuid.uuid4())
    }


def login_to_gradescope(email, password):
    """
    Login to Gradescope and return session object 

    Args: 
        email (str): Gradescope account email 
        password (str): Gradescope account password 

    Returns: 
        requests.Session: logged in session object 

    Raises: 
        Exception: Login Exception thrown on failure
    """

    session = requests.Session()
    headers = anti_cache_headers()
    session.headers.update(headers)

    login_page = session.get("https://www.gradescope.com/login")
    soup = BeautifulSoup(login_page.text, 'html.parser')

    csrf_token = soup.find('input', {'name': 'authenticity_token'})['value']

    payload = {
        'utf8': '✓',
        'authenticity_token': csrf_token,
        'session[email]': email,
        'session[password]': password,
        'commit': 'Log In'
    }

    resp = session.post("https://www.gradescope.com/login", data=payload)

    if "Log Out" not in resp.text:
        raise Exception("❌  Login failed, please check your email address and password")

    print("✅ Login successfully to start getting the submission list...")
    return session


def get_assignment_id(session, course_id):
    url = f'https://www.gradescope.com/courses/{course_id}/assignments'
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # find the React component containing assignment data
    assignment_table = soup.find('div', {'data-react-class': 'AssignmentsTable'})
    
    # initialize the result dictionary
    result = dict()
    
    if assignment_table:
        # extract React props data
        data_props = assignment_table.get('data-react-props', '{}').replace('&quot;', '"')
        
        try:
            # parse JSON data
            assignments_data = json.loads(data_props)
            
            # extract assignment information
            for item in assignments_data.get('table_data', []):
                if 'title' in item and 'id' in item:
                    title = item['title']
                    assignment_id = item['id'].split('_')[1]
                    result[title] = assignment_id
        except:
            pass
    
    return result
    

def get_course_id(session):
    url = f'https://www.gradescope.com/'
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    

        # 找到 "Instructor Courses" 标题
    instructor_heading = soup.find('h1', string='Instructor Courses')
    if not instructor_heading:
        print("No Instructor Courses Found.")
        return {}
    
    # 找到 instructor courses 的容器
    course_list = instructor_heading.find_next('div', class_='courseList')
    if not course_list:
        print("Not Instructor Courses list Found.")
        return {}
    # find all course lists
    #course_list = soup.find('div', class_='courseList')
    
    # initialize the result dictionary
    result = dict()
    
    # find all terms
    terms = course_list.find_all('div', class_='courseList--term')
    
    # pocess each term
    for term in terms:
        term_name = term.text
        # get all courses for this term
        next_element = term.find_next_sibling('div', class_='courseList--coursesForTerm')
        if next_element:
            course_boxes = next_element.find_all('a', class_='courseBox')
            for course in course_boxes:
                course_id = course.get('href').split('/')[-1]
                shortname = course.find('h3', class_='courseBox--shortname').text if course.find('h3', class_='courseBox--shortname') else "无"
                
                # create course info dictionary entry
                key = f"{term_name} - {shortname}"
                result[key] = course_id
                
    return result


def check_id(session, course_id, assignment_id = None):
    """
    Checks if a course ID or assignment ID on Gradescope is valid.
    
    Parameters:
        session: Logged-in session object used to send HTTP requests
        course_id: The course ID to check
        assignment_id: Optional parameter, the assignment ID to check, defaults to None
    
    Returns:
        bool: True if the ID is valid and the user has permission to access it; False otherwise
    """   
    if assignment_id is None:
        url = f'https://www.gradescope.com/courses/{course_id}'
    else:
        url = f'https://www.gradescope.com/courses/{course_id}/assignments/{assignment_id}/submissions'
    
    response = session.get(url)
    
    if response.status_code == 404:
        print("404 Not Found!")
        return False
    elif 'You are not authorized to access this page' in response.text:
        print("Not authorized ID!")
        return False
    else:
        return True


def input_correct_id(session, course_id, assignment_id = None):
    """
    Prompts the user to input the correct course ID or assignment ID until a valid ID is entered or the user chooses to quit.
    
    Parameters:
        session: Logged-in session object used to verify the ID
        course_id: Initial course ID to check
        assignment_id: Optional parameter, initial assignment ID to check, defaults to None
    
    Returns:
        str: Valid course ID or assignment ID; None if the user chooses to quit
    """
    if assignment_id is None:
        while check_id(session, course_id) is not True:
            course_id = input("Wrong course id, input the correct on (Enter q to quit)\n")
            if course_id == "q":
                return
        return course_id
    else:
        while check_id(session, course_id, assignment_id) is not True:
            assignment_id = input("Wrong assignment id, input the correct on (Enter q to quit)\n")
            if assignment_id == "q":
                return
        return assignment_id
