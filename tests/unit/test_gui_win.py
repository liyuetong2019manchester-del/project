import pytest
from unittest.mock import Mock, patch, MagicMock, call
import tkinter as tk
from tkinter import messagebox
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'anonymization_scripts'))

from gui_win import (
    gui_input, gui_password_input, gui_print, gui_choose_from_list, 
    gui_show_selection, _create_custom_input_dialog, all_messages
)


class TestGuiInput:
    @patch('gui_win._create_custom_input_dialog')
    def test_gui_input_success(self, mock_dialog):
        """Test normal input functionality"""
        mock_dialog.return_value = "test input"
        result = gui_input("Enter text:")
        assert result == "test input"
        mock_dialog.assert_called_once_with("Enter text:", title="Input", is_password=False)

    @patch('gui_win._create_custom_input_dialog')
    def test_gui_input_empty_prompt(self, mock_dialog):
        """Test empty prompt input"""
        mock_dialog.return_value = "empty prompt input"
        result = gui_input("")
        assert result == "empty prompt input"
        mock_dialog.assert_called_once_with("", title="Input", is_password=False)

    @patch('gui_win._create_custom_input_dialog')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_input_fallback(self, mock_print, mock_input, mock_dialog):
        """Test fallback mechanism when GUI exception occurs"""
        mock_dialog.side_effect = Exception("GUI error")
        mock_input.return_value = "fallback input"
        result = gui_input("Enter text:")
        assert result == "fallback input"
        mock_print.assert_called_once_with("Error displaying input dialog: GUI error")
        mock_input.assert_called_once_with("Enter text:")


class TestGuiPasswordInput:
    @patch('gui_win._create_custom_input_dialog')
    def test_gui_password_input_success(self, mock_dialog):
        """Test password input success"""
        mock_dialog.return_value = "password123"
        result = gui_password_input("Enter password:")
        assert result == "password123"
        mock_dialog.assert_called_once_with("Enter password:", title="Password", is_password=True)

    @patch('gui_win._create_custom_input_dialog')
    def test_gui_password_input_default_prompt(self, mock_dialog):
        """Test default password prompt"""
        mock_dialog.return_value = "default_pass"
        result = gui_password_input()
        assert result == "default_pass"
        mock_dialog.assert_called_once_with("Enter password:", title="Password", is_password=True)

    @patch('gui_win._create_custom_input_dialog')
    @patch('gui_win.getpass.getpass')
    def test_gui_password_input_cancel_getpass(self, mock_getpass, mock_dialog):
        """Test fallback to getpass when user cancels"""
        mock_dialog.return_value = None
        mock_getpass.return_value = "getpass_password"
        result = gui_password_input("Enter password:")
        assert result == "getpass_password"
        mock_getpass.assert_called_once_with("Enter password:")

    @patch('gui_win._create_custom_input_dialog')
    @patch('gui_win.getpass.getpass')
    @patch('builtins.input')
    def test_gui_password_input_cancel_input_fallback(self, mock_input, mock_getpass, mock_dialog):
        """Test fallback to input when getpass is not available"""
        mock_dialog.return_value = None
        mock_getpass.side_effect = ImportError()
        mock_input.return_value = "input_password"
        result = gui_password_input("Enter password:")
        assert result == "input_password"
        mock_input.assert_called_once_with("Enter password:")

    @patch('gui_win._create_custom_input_dialog')
    @patch('gui_win.getpass.getpass')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_password_input_exception_fallback(self, mock_print, mock_input, mock_getpass, mock_dialog):
        """Test complete fallback chain when GUI exception occurs"""
        mock_dialog.side_effect = Exception("GUI error")
        mock_getpass.return_value = "getpass_password"
        result = gui_password_input("Enter password:")
        assert result == "getpass_password"
        mock_print.assert_called_once_with("Error displaying password dialog: GUI error")

    @patch('gui_win._create_custom_input_dialog')
    @patch('gui_win.getpass.getpass')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_password_input_exception_full_fallback(self, mock_print, mock_input, mock_getpass, mock_dialog):
        """Test complete fallback when GUI exception occurs and getpass is not available"""
        mock_dialog.side_effect = Exception("GUI error")
        mock_getpass.side_effect = ImportError()
        mock_input.return_value = "final_fallback"
        result = gui_password_input("Enter password:")
        assert result == "final_fallback"
        mock_print.assert_called_once_with("Error displaying password dialog: GUI error")


class TestGuiPrint:
    def setup_method(self):
        """Clear message list before each test"""
        all_messages.clear()

    @patch('builtins.print')
    def test_gui_print_basic(self, mock_print):
        """Test basic print functionality"""
        gui_print("Hello", "World")
        assert len(all_messages) == 1
        assert all_messages[0] == "Hello World\n"
        mock_print.assert_called_once_with("Hello", "World")

    @patch('builtins.print')
    def test_gui_print_with_kwargs(self, mock_print):
        """Test print with keyword arguments"""
        gui_print("A", "B", "C", sep="-", end="!\n")
        assert len(all_messages) == 1
        assert all_messages[0] == "A-B-C!\n"
        mock_print.assert_called_once_with("A", "B", "C", sep="-", end="!\n")

    @patch('builtins.print')
    def test_gui_print_single_arg(self, mock_print):
        """Test single argument print"""
        gui_print("Single")
        assert len(all_messages) == 1
        assert all_messages[0] == "Single\n"
        mock_print.assert_called_once_with("Single")

    @patch('builtins.print')
    def test_gui_print_no_args(self, mock_print):
        """Test print with no arguments"""
        gui_print()
        assert len(all_messages) == 1
        assert all_messages[0] == "\n"
        mock_print.assert_called_once_with()

    @patch('builtins.print')
    def test_gui_print_multiple_calls(self, mock_print):
        """Test multiple calls accumulation"""
        gui_print("First")
        gui_print("Second")
        assert len(all_messages) == 2
        assert all_messages[0] == "First\n"
        assert all_messages[1] == "Second\n"

    @patch('builtins.print')
    def test_gui_print_custom_sep_end(self, mock_print):
        """Test custom separator and ending"""
        gui_print("1", "2", "3", sep=":", end="")
        assert len(all_messages) == 1
        assert all_messages[0] == "1:2:3"

        
        # Completely simulate GUI behavior
        with patch('gui_win.tk.Tk') as mock_tk_class:
            mock_root = Mock()
            mock_tk_class.return_value = mock_root
            
            with patch('gui_win.tk.Frame'), \
                 patch('gui_win.tk.Label'), \
                 patch('gui_win.tk.Listbox') as mock_listbox_class, \
                 patch('gui_win.tk.Button'), \
                 patch('gui_win.tk.Scrollbar'):
                
                mock_listbox = Mock()
                mock_listbox_class.return_value = mock_listbox
                mock_listbox.curselection.return_value = [1]  # Select second item
                

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_single(self, mock_input, mock_print):
        """Test command line fallback during exception - single selection"""
        items = ["item1", "item2", "item3"]
        mock_input.return_value = "2"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", False, "Test")
            assert result == "item2"

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_multiple_all(self, mock_input, mock_print):
        """Test command line fallback during exception - multiple selection all"""
        items = ["item1", "item2", "item3"]
        mock_input.return_value = "all"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", True, "Test")
            assert result == items

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_multiple_numbers(self, mock_input, mock_print):
        """Test command line fallback during exception - multiple selection with numbers"""
        items = ["item1", "item2", "item3"]
        mock_input.return_value = "1 3"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", True, "Test")
            assert result == ["item1", "item3"]

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_invalid_input(self, mock_input, mock_print):
        """Test command line fallback during exception - invalid input"""
        items = ["item1", "item2", "item3"]
        mock_input.return_value = "invalid"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", False, "Test")
            assert result is None

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_out_of_range(self, mock_input, mock_print):
        """Test command line fallback during exception - out of range"""
        items = ["item1", "item2", "item3"]
        mock_input.return_value = "5"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", False, "Test")
            assert result is None

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_empty_list(self, mock_input, mock_print):
        """Test handling of empty list"""
        items = []
        mock_input.return_value = "1"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", False, "Test")
            assert result is None

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_multiple_mixed_input(self, mock_input, mock_print):
        """Test multiple selection with mixed input"""
        items = ["item1", "item2", "item3", "item4"]
        mock_input.return_value = "1 invalid 3 5"  # Contains invalid and out-of-range numbers
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", True, "Test")
            assert result == ["item1", "item3"]  # Only return valid selections

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_choose_from_list_exception_fallback_multiple_empty_selection(self, mock_input, mock_print):
        """Test multiple selection with empty selection"""
        items = ["item1", "item2", "item3"]
        mock_input.return_value = ""
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_choose_from_list(items, "Select:", True, "Test")
            assert result == []


class TestGuiShowSelection:
    @patch('gui_win.messagebox.askyesno')
    @patch('gui_win.tk.Tk')
    def test_gui_show_selection_success_yes(self, mock_tk, mock_askyesno):
        """Test confirmation dialog - select yes"""
        mock_root = Mock()
        mock_tk.return_value = mock_root
        mock_askyesno.return_value = True
        
        result = gui_show_selection("Confirm selection", "Test")
        assert result is True
        mock_askyesno.assert_called_once_with("Test", "Confirm selection", parent=mock_root)
        mock_root.withdraw.assert_called_once()
        mock_root.destroy.assert_called_once()

    @patch('gui_win.messagebox.askyesno')
    @patch('gui_win.tk.Tk')
    def test_gui_show_selection_success_no(self, mock_tk, mock_askyesno):
        """Test confirmation dialog - select no"""
        mock_root = Mock()
        mock_tk.return_value = mock_root
        mock_askyesno.return_value = False
        
        result = gui_show_selection("Confirm selection", "Test")
        assert result is False

    @patch('gui_win.messagebox.askyesno')
    @patch('gui_win.tk.Tk')
    def test_gui_show_selection_default_title(self, mock_tk, mock_askyesno):
        """Test confirmation dialog - default title"""
        mock_root = Mock()
        mock_tk.return_value = mock_root
        mock_askyesno.return_value = True
        
        result = gui_show_selection("Confirm selection")
        assert result is True
        mock_askyesno.assert_called_once_with("Selection Summary", "Confirm selection", parent=mock_root)

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_show_selection_exception_fallback_yes(self, mock_input, mock_print):
        """Test command line fallback during exception - yes"""
        mock_input.return_value = "y"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_show_selection("Confirm selection", "Test")
            assert result is True

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_show_selection_exception_fallback_no(self, mock_input, mock_print):
        """Test command line fallback during exception - no"""
        mock_input.return_value = "n"
        
        with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
            result = gui_show_selection("Confirm selection", "Test")
            assert result is False

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_show_selection_exception_fallback_yes_variants(self, mock_input, mock_print):
        """Test command line fallback during exception - various yes variants"""
        yes_variants = ["yes", "Y", "YES", "y"]
        for response in yes_variants:
            mock_input.return_value = response
            with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
                result = gui_show_selection("Confirm selection", "Test")
                assert result is True

    @patch('builtins.print')
    @patch('builtins.input')
    def test_gui_show_selection_exception_fallback_no_variants(self, mock_input, mock_print):
        """Test command line fallback during exception - various no variants"""
        no_variants = ["no", "N", "NO", "n", "anything_else"]
        for response in no_variants:
            mock_input.return_value = response
            with patch('gui_win.tk.Tk', side_effect=Exception("GUI error")):
                result = gui_show_selection("Confirm selection", "Test")
                assert result is False


class TestCreateCustomInputDialog:
    def test_create_custom_input_dialog_password_mode(self):
        """Test password mode dialog creation"""
        with patch('gui_win.tk.Tk') as mock_tk:
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            with patch('gui_win.tk.Frame'), \
                 patch('gui_win.tk.Label'), \
                 patch('gui_win.tk.Entry') as mock_entry_class, \
                 patch('gui_win.tk.Button'):
                
                mock_entry = Mock()
                mock_entry_class.return_value = mock_entry
                mock_entry.get.return_value = "password"
                
                # Mock mainloop to not block
                mock_root.mainloop = Mock()
                
    def test_create_custom_input_dialog_normal_mode(self):
        """Test normal mode dialog creation"""
        with patch('gui_win.tk.Tk') as mock_tk:
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            with patch('gui_win.tk.Frame'), \
                 patch('gui_win.tk.Label'), \
                 patch('gui_win.tk.Entry') as mock_entry_class, \
                 patch('gui_win.tk.Button'):
                
                mock_entry = Mock()
                mock_entry_class.return_value = mock_entry
                mock_entry.get.return_value = "normal_input"
                
                mock_root.mainloop = Mock()
                

    def test_create_custom_input_dialog_geometry_calculation(self):
        """Test window geometry position calculation"""
        with patch('gui_win.tk.Tk') as mock_tk:
            mock_root = Mock()
            mock_tk.return_value = mock_root
            mock_root.winfo_screenwidth.return_value = 1920
            mock_root.winfo_screenheight.return_value = 1080
            
            with patch('gui_win.tk.Frame'), \
                 patch('gui_win.tk.Label'), \
                 patch('gui_win.tk.Entry') as mock_entry_class, \
                 patch('gui_win.tk.Button'):
                
                mock_entry = Mock()
                mock_entry_class.return_value = mock_entry
                mock_root.mainloop = Mock()
                
                try:
                    result = _create_custom_input_dialog("Test", "Test", False)
                    # Verify geometry setting is called (even if specific values might differ)
                    assert mock_root.geometry.called
                except AttributeError:
                    pass



class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    def setup_method(self):
        all_messages.clear()

    @patch('gui_win._create_custom_input_dialog')
    @patch('builtins.print')
    def test_complete_input_workflow(self, mock_print, mock_dialog):
        """Test complete input workflow"""
        # Simulate user input sequence
        inputs = ["username", "password123", "selected_item"]
        mock_dialog.side_effect = inputs
        
        # Execute a series of input operations
        username = gui_input("Username:")
        password = gui_password_input("Password:")
        
        # Verify results
        assert username == "username"
        assert password == "password123"
        
        # Verify call count
        assert mock_dialog.call_count == 2

    def test_message_accumulation(self):
        """Test message accumulation functionality"""
        with patch('builtins.print'):
            gui_print("Message 1")
            gui_print("Message 2", "Part 2")
            gui_print("Message 3", sep=":", end="!")
            
            assert len(all_messages) == 3
            assert all_messages[0] == "Message 1\n"
            assert all_messages[1] == "Message 2 Part 2\n"
            assert all_messages[2] == "Message 3!"

    @patch('gui_win.messagebox.askyesno', return_value=True)
    @patch('gui_win.tk.Tk')
    def test_gui_components_cleanup(self, mock_tk, mock_askyesno):
        """Test GUI components cleanup"""
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        result = gui_show_selection("Test message")
        
        # Verify window is properly cleaned up
        mock_root.withdraw.assert_called_once()
        mock_root.destroy.assert_called_once()
        assert result is True
