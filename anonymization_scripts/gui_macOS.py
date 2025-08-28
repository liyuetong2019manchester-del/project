import subprocess


# for storing all printed messages
all_messages = []


def gui_input(prompt=""):
    """
    use macOS dialog box instead of standard input function
    
    Args:
        prompt (str): prompt message
    
    Returns:
        str: text entered by the user
    """
    # clean prompt (replace line breaks, etc.)
    prompt = prompt.replace('\n', '\\n')
    
    script = f'''
    tell application "System Events"
        activate
        set dialogResult to display dialog "{prompt}" default answer "" with title "Input"
        set userInput to text returned of dialogResult
        return userInput
    end tell
    '''
    
    try:
        # execute AppleScript
        result = subprocess.run(['osascript', '-e', script], 
                               capture_output=True, 
                               text=True)
        
        if result.returncode != 0:
            # if dialog is canceled, fall back to standard input
            return input(prompt)
            
        return result.stdout.strip()
        
    except Exception as e:
        # if error occurs, fall back to standard input
        print(f"Error displaying input dialog: {e}")
        return input(prompt)


def gui_password_input(prompt="Enter password:"):
    """
    use macOS dialog box instead of password input
    
    Args:
        prompt (str): prompt message
    
    Returns:
        str: password entered by the user
    """
    # clean prompt
    prompt = prompt.replace('\n', '\\n')
    
    script = f'''
    tell application "System Events"
        activate
        set dialogResult to display dialog "{prompt}" default answer "" with hidden answer with title "Password"
        set userInput to text returned of dialogResult
        return userInput
    end tell
    '''
    
    try:
        # execute AppleScript
        result = subprocess.run(['osascript', '-e', script], 
                               capture_output=True, 
                               text=True)
        
        if result.returncode != 0:
            # if dialog is canceled, fall back to getpass
            try:
                import getpass
                return getpass.getpass(prompt)
            except ImportError:
                return input(prompt)  # last fallback option
            
        return result.stdout.strip()
        
    except Exception as e:
        # if error occurs, fall back to getpass
        print(f"Error displaying password dialog: {e}")
        try:
            import getpass
            return getpass.getpass(prompt)
        except ImportError:
            return input(prompt)


def gui_print(*args, **kwargs):
    """
    replace standard print function, output to console and store in message list
    
    Args:
        *args: objects to print
        **kwargs: keyword arguments, same as standard print
    """
    # format output, similar to standard print
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    message = sep.join(str(arg) for arg in args) + end
    
    # add to message list
    all_messages.append(message)
    
    # also output to standard output
    print(*args, **kwargs)


def gui_choose_from_list(items, prompt="Select an item:", multiple=False, title="Selection"):
    """
    display clickable list selection dialog
    
    Args:
        items (list): list of options
        prompt (str): prompt message
        multiple (bool): whether to allow multiple selection
        title (str): dialog title
    
    Returns:
        if multiple=False:
            str: selected item, or None if canceled
        if multiple=True:
            list: list of selected items, or empty list if canceled
    """
    # build AppleScript
    multiple_cmd = " with multiple selections allowed" if multiple else ""
    items_str = ", ".join([f'"{item}"' for item in items])
    
    script = f'''
    tell application "System Events"
        activate
        set itemList to {{{items_str}}}
        set selectedItems to choose from list itemList with prompt "{prompt}"{multiple_cmd} with title "{title}"
        
        if selectedItems is false then
            return "cancelled"
        else
            set selectedText to ""
            repeat with i from 1 to count of selectedItems
                set selectedText to selectedText & item i of selectedItems
                if i is not (count of selectedItems) then
                    set selectedText to selectedText & "|"
                end if
            end repeat
            return selectedText
        end if
    end tell
    '''
    
    try:
        # execute AppleScript
        result = subprocess.run(['osascript', '-e', script], 
                               capture_output=True, 
                               text=True)
        
        # check for cancellation or error
        if result.returncode != 0 or result.stdout.strip() == "cancelled":
            return [] if multiple else None
            
        # process results
        selected = result.stdout.strip()
        
        if multiple:
            # return list for multiple selection
            return selected.split('|')
        else:
            # return string for single selection
            return selected
            
    except Exception as e:
        print(f"Error displaying selection dialog: {e}")
        # fall back to command line
        print(f"\n{prompt}")
        
        for i, item in enumerate(items):
            print(f"{i+1}. {item}")
        
        if multiple:
            selection = input("Enter numbers (space-separated) or 'all': ")
            
            if selection.lower() == 'all':
                return items
                
            try:
                indices = [int(idx) - 1 for idx in selection.split() if idx.strip().isdigit()]
                return [items[i] for i in indices if 0 <= i < len(items)]
            except:
                return []
        else:
            selection = input("Enter number: ")
            
            try:
                idx = int(selection) - 1
                if 0 <= idx < len(items):
                    return items[idx]
            except:
                pass
                
            return None


def gui_show_selection(message, title="Selection Summary"):
    """
    display confirmation dialog for selection results
    
    Args:
        message (str): message to display, usually a selection summary
        title (str): dialog title
    
    Returns:
        bool: True if user confirms selection, False otherwise
    """
    # clean message
    message = message.replace('\n', '\\n').replace('"', '\\"')
    
    script = f'''
    tell application "System Events"
        activate
        set theResult to button returned of (display dialog "{message}" buttons {{"Cancel", "OK"}} default button "OK" with title "{title}")
        return theResult
    end tell
    '''
    
    try:
        # execute AppleScript
        result = subprocess.run(['osascript', '-e', script], 
                               capture_output=True, 
                               text=True)
        
        # check if user clicked the OK button
        if result.returncode != 0 or "Cancel" in result.stdout:
            return False
            
        return True
        
    except Exception as e:
        print(f"Error displaying confirmation dialog: {e}")
        # fall back to command line
        print(f"\n{message}")
        response = input("Proceed? (y/n): ")
        return response.lower() in ['y', 'yes']