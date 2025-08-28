import pytest
from unittest.mock import patch, MagicMock
import subprocess
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from gui_macOS import (
    gui_input, gui_password_input, gui_print, gui_choose_from_list, 
    gui_show_selection, all_messages
)


class TestGuiInput:
    @patch('subprocess.run')
    def test_gui_input_success(self, mock_run):
        # Mock successful AppleScript execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test input\n"
        mock_run.return_value = mock_result
        
        result = gui_input("Enter text:")
        assert result == "test input"
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('builtins.input')
    def test_gui_input_fallback_on_error_code(self, mock_input, mock_run):
        # Mock failed AppleScript execution
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        mock_input.return_value = "fallback input"
        
        result = gui_input("Enter text:")
        assert result == "fallback input"
        mock_input.assert_called_once_with("Enter text:")
    
    @patch('subprocess.run')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_input_fallback_on_exception(self, mock_print, mock_input, mock_run):
        # Mock subprocess exception
        mock_run.side_effect = Exception("Test error")
        mock_input.return_value = "fallback input"
        
        result = gui_input("Enter text:")
        assert result == "fallback input"
        mock_print.assert_called_once_with("Error displaying input dialog: Test error")
    
    def test_gui_input_prompt_cleaning(self):
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test\n"
            mock_run.return_value = mock_result
            
            gui_input("Line 1\nLine 2")
            # Check that the script contains escaped newlines
            call_args = mock_run.call_args[0][0]
            assert "Line 1\\nLine 2" in call_args[2]


class TestGuiPasswordInput:
    @patch('subprocess.run')
    def test_gui_password_input_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "secret123\n"
        mock_run.return_value = mock_result
        
        result = gui_password_input("Enter password:")
        assert result == "secret123"
    
    @patch('subprocess.run')
    @patch('getpass.getpass')
    def test_gui_password_input_fallback_getpass(self, mock_getpass, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        mock_getpass.return_value = "fallback_password"
        
        result = gui_password_input("Enter password:")
        assert result == "fallback_password"
    

class TestGuiPrint:
    def test_gui_print_basic(self):
        # Clear all_messages before test
        all_messages.clear()
        
        with patch('builtins.print') as mock_print:
            gui_print("Hello", "World")
            
            # Check message was stored
            assert len(all_messages) == 1
            assert all_messages[0] == "Hello World\n"
            
            # Check print was called
            mock_print.assert_called_once_with("Hello", "World")
    
    def test_gui_print_with_kwargs(self):
        all_messages.clear()
        
        with patch('builtins.print') as mock_print:
            gui_print("A", "B", sep="-", end="!")
            
            assert all_messages[0] == "A-B!"
            mock_print.assert_called_once_with("A", "B", sep="-", end="!")


class TestGuiChooseFromList:
    @patch('subprocess.run')
    def test_gui_choose_from_list_single_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "option2\n"
        mock_run.return_value = mock_result
        
        items = ["option1", "option2", "option3"]
        result = gui_choose_from_list(items, multiple=False)
        assert result == "option2"
    
    @patch('subprocess.run')
    def test_gui_choose_from_list_multiple_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "option1|option3\n"
        mock_run.return_value = mock_result
        
        items = ["option1", "option2", "option3"]
        result = gui_choose_from_list(items, multiple=True)
        assert result == ["option1", "option3"]
    
    @patch('subprocess.run')
    def test_gui_choose_from_list_cancelled(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "cancelled\n"
        mock_run.return_value = mock_result
        
        items = ["option1", "option2"]
        result_single = gui_choose_from_list(items, multiple=False)
        result_multiple = gui_choose_from_list(items, multiple=True)
        
        assert result_single is None
        assert result_multiple == []
    
    @patch('subprocess.run')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_choose_from_list_fallback_single(self, mock_print, mock_input, mock_run):
        mock_run.side_effect = Exception("Test error")
        mock_input.return_value = "2"
        
        items = ["option1", "option2", "option3"]
        result = gui_choose_from_list(items, multiple=False)
        assert result == "option2"
    
    @patch('subprocess.run')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_choose_from_list_fallback_multiple_all(self, mock_print, mock_input, mock_run):
        mock_run.side_effect = Exception("Test error")
        mock_input.return_value = "all"
        
        items = ["option1", "option2", "option3"]
        result = gui_choose_from_list(items, multiple=True)
        assert result == items
    
    @patch('subprocess.run')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_choose_from_list_fallback_multiple_indices(self, mock_print, mock_input, mock_run):
        mock_run.side_effect = Exception("Test error")
        mock_input.return_value = "1 3"
        
        items = ["option1", "option2", "option3"]
        result = gui_choose_from_list(items, multiple=True)
        assert result == ["option1", "option3"]


class TestGuiShowSelection:
    @patch('subprocess.run')
    def test_gui_show_selection_ok(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "OK\n"
        mock_run.return_value = mock_result
        
        result = gui_show_selection("Confirm selection?")
        assert result is True
    
    @patch('subprocess.run')
    def test_gui_show_selection_cancel(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Cancel\n"
        mock_run.return_value = mock_result
        
        result = gui_show_selection("Confirm selection?")
        assert result is False
    
    @patch('subprocess.run')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_show_selection_fallback_yes(self, mock_print, mock_input, mock_run):
        mock_run.side_effect = Exception("Test error")
        mock_input.return_value = "y"
        
        result = gui_show_selection("Confirm selection?")
        assert result is True
    
    @patch('subprocess.run')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_gui_show_selection_fallback_no(self, mock_print, mock_input, mock_run):
        mock_run.side_effect = Exception("Test error")
        mock_input.return_value = "n"
        
        result = gui_show_selection("Confirm selection?")
        assert result is False
    
    def test_gui_show_selection_message_cleaning(self):
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "OK\n"
            mock_run.return_value = mock_result
            
            gui_show_selection('Line 1\nLine 2 "quoted"')
            # Check that the script contains escaped characters
            call_args = mock_run.call_args[0][0]
            assert 'Line 1\\nLine 2 \\"quoted\\"' in call_args[2]