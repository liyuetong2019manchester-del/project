import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import getpass

# for storing all printed messages
all_messages = []


def _create_custom_input_dialog(prompt, title="Input", is_password=False):
    """
    Create a custom input dialog with better size and appearance
    """
    root = tk.Tk()
    root.title(title)
    root.lift()
    root.attributes('-topmost', True)

    # Set window size and center it
    window_width = 500
    window_height = 220
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)

    # Configure style
    root.configure(bg='#f0f0f0')

    result = None

    def on_ok():
        nonlocal result
        result = entry.get()
        root.quit()

    def on_cancel():
        nonlocal result
        result = None
        root.quit()

    def on_enter(event):
        on_ok()

    # Create main frame with padding
    main_frame = tk.Frame(root, bg='#f0f0f0', padx=25, pady=25)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Prompt label with better font
    prompt_label = tk.Label(
        main_frame,
        text=prompt,
        font=('Segoe UI', 11),
        bg='#f0f0f0',
        wraplength=450,
        justify=tk.LEFT
    )
    prompt_label.pack(pady=(0, 20))

    # Entry widget with better styling
    entry_frame = tk.Frame(main_frame, bg='#f0f0f0')
    entry_frame.pack(fill=tk.X, pady=(0, 25))

    entry = tk.Entry(
        entry_frame,
        font=('Segoe UI', 12),
        width=40,
        relief=tk.SOLID,
        bd=1,
        highlightthickness=2,
        highlightcolor='#0078d4',
        highlightbackground='#cccccc'
    )

    if is_password:
        entry.config(show='●')

    entry.pack(ipady=8)
    entry.bind('<Return>', on_enter)
    entry.focus_set()

    # Button frame
    button_frame = tk.Frame(main_frame, bg='#f0f0f0')
    button_frame.pack(fill=tk.X)

    # Cancel button
    cancel_btn = tk.Button(
        button_frame,
        text="Cancel",
        command=on_cancel,
        font=('Segoe UI', 10),
        width=12,
        height=1,
        relief=tk.FLAT,
        bg='#e1e1e1',
        activebackground='#d1d1d1',
        cursor='hand2'
    )
    cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

    # OK button
    ok_btn = tk.Button(
        button_frame,
        text="OK",
        command=on_ok,
        font=('Segoe UI', 10, 'bold'),
        width=12,
        height=1,
        relief=tk.FLAT,
        bg='#0078d4',
        fg='white',
        activebackground='#106ebe',
        activeforeground='white',
        cursor='hand2'
    )
    ok_btn.pack(side=tk.RIGHT)

    # Handle window close
    root.protocol("WM_DELETE_WINDOW", on_cancel)

    # Run the dialog
    root.mainloop()
    root.destroy()

    return result


def gui_input(prompt=""):
    """
    use Windows dialog box instead of standard input function

    Args:
        prompt (str): prompt message

    Returns:
        str: text entered by the user
    """
    try:
        # Create custom input dialog for better size control
        return _create_custom_input_dialog(prompt, title="Input", is_password=False)

    except Exception as e:
        # if error occurs, fall back to standard input
        print(f"Error displaying input dialog: {e}")
        return input(prompt)


def gui_password_input(prompt="Enter password:"):
    """
    use Windows dialog box instead of password input

    Args:
        prompt (str): prompt message

    Returns:
        str: password entered by the user
    """
    try:
        # Create custom password dialog
        result = _create_custom_input_dialog(prompt, title="Password", is_password=True)

        if result is None:
            # User clicked cancel, fall back to getpass
            try:
                return getpass.getpass(prompt)
            except ImportError:
                return input(prompt)  # last fallback option

        return result

    except Exception as e:
        # if error occurs, fall back to getpass
        print(f"Error displaying password dialog: {e}")
        try:
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
    try:
        # Create main window
        root = tk.Tk()
        root.title(title)
        root.lift()  # Bring to front
        root.attributes('-topmost', True)  # Keep on top

        # Set better window size and center it
        window_width = 500
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.resizable(True, True)
        root.configure(bg='#f0f0f0')

        # Variables to store result
        result = None

        def on_ok():
            nonlocal result
            if multiple:
                # Get all selected items
                selected_indices = listbox.curselection()
                result = [items[i] for i in selected_indices]
            else:
                # Get single selected item
                selected_indices = listbox.curselection()
                if selected_indices:
                    result = items[selected_indices[0]]
                else:
                    result = None
            root.quit()

        def on_cancel():
            nonlocal result
            result = [] if multiple else None
            root.quit()

        def on_select_all():
            if multiple:
                listbox.select_set(0, tk.END)

        def on_clear_all():
            if multiple:
                listbox.selection_clear(0, tk.END)

        # Create main frame with padding
        main_frame = tk.Frame(root, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Prompt label with better font
        prompt_label = tk.Label(
            main_frame,
            text=prompt,
            font=('Segoe UI', 11),
            bg='#f0f0f0',
            wraplength=460,
            justify=tk.LEFT
        )
        prompt_label.pack(pady=(0, 15), fill=tk.X)

        # Create frame for listbox and scrollbar
        list_frame = tk.Frame(main_frame, bg='#f0f0f0')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Create listbox with scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        select_mode = tk.EXTENDED if multiple else tk.SINGLE
        listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            selectmode=select_mode,
            font=('Segoe UI', 10),
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightcolor='#0078d4'
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=listbox.yview)

        # Add items to listbox
        for item in items:
            listbox.insert(tk.END, item)

        # Double-click to select (for single selection)
        def on_double_click(event):
            if not multiple:
                on_ok()

        listbox.bind("<Double-Button-1>", on_double_click)

        # Create button frame
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X)

        if multiple:
            # Add Select All and Clear buttons for multiple selection
            select_all_btn = tk.Button(
                button_frame,
                text="Select All",
                command=on_select_all,
                font=('Segoe UI', 9),
                relief=tk.FLAT,
                bg='#e1e1e1',
                activebackground='#d1d1d1',
                cursor='hand2'
            )
            select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

            clear_all_btn = tk.Button(
                button_frame,
                text="Clear All",
                command=on_clear_all,
                font=('Segoe UI', 9),
                relief=tk.FLAT,
                bg='#e1e1e1',
                activebackground='#d1d1d1',
                cursor='hand2'
            )
            clear_all_btn.pack(side=tk.LEFT, padx=(0, 15))

        # OK and Cancel buttons
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=on_cancel,
            font=('Segoe UI', 10),
            width=10,
            relief=tk.FLAT,
            bg='#e1e1e1',
            activebackground='#d1d1d1',
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

        ok_btn = tk.Button(
            button_frame,
            text="OK",
            command=on_ok,
            font=('Segoe UI', 10, 'bold'),
            width=10,
            relief=tk.FLAT,
            bg='#0078d4',
            fg='white',
            activebackground='#106ebe',
            activeforeground='white',
            cursor='hand2'
        )
        ok_btn.pack(side=tk.RIGHT)

        # Handle window close
        root.protocol("WM_DELETE_WINDOW", on_cancel)

        # Set focus and run
        root.focus_force()
        root.mainloop()
        root.destroy()

        return result

    except Exception as e:
        print(f"Error displaying selection dialog: {e}")
        # fall back to command line
        print(f"\n{prompt}")

        for i, item in enumerate(items):
            print(f"{i + 1}. {item}")

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
    try:
        # Create a hidden root window
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.lift()  # Bring to front
        root.attributes('-topmost', True)  # Keep on top

        # Show confirmation dialog
        result = messagebox.askyesno(title, message, parent=root)
        root.destroy()

        return result

    except Exception as e:
        print(f"Error displaying confirmation dialog: {e}")
        # fall back to command line
        print(f"\n{message}")
        response = input("Proceed? (y/n): ")
        return response.lower() in ['y', 'yes']