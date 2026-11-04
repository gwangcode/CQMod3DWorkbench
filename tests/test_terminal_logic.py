import sys
import os
from unittest.mock import MagicMock, patch

# --- 1. 打桩 FreeCAD 和 PySide ---
sys.modules['FreeCAD'] = MagicMock()
sys.modules['FreeCADGui'] = MagicMock()
sys.modules['Part'] = MagicMock()
sys.modules['PySide'] = MagicMock()
sys.modules['PySide.QtGui'] = MagicMock()
sys.modules['PySide.QtCore'] = MagicMock()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import terminal

def test_terminal_execution_namespace():
    # 绕过 Qt 的初始化
    term = terminal.PythonTerminal()
    
    term.write = MagicMock()
    term.insertPlainText = MagicMock()
    
    term.execute_code("test_x = 42")
    assert term.local_vars.get("test_x") == 42
    
    term.local_vars["show"] = MagicMock()
    term.execute_code("show('dummy_model')")
    term.local_vars["show"].assert_called_once_with("dummy_model")
    
    code = """
def multiply(a, b):
    return a * b
res = multiply(3, 4)
"""
    term.execute_code(code)
    assert term.local_vars.get("res") == 12

def test_terminal_error_handling():
    term = terminal.PythonTerminal()
    term.write = MagicMock()
    term.execute_code("print(1/0)")
    
    term.write.assert_called_once()
    assert "ZeroDivisionError" in term.write.call_args[0][0]
