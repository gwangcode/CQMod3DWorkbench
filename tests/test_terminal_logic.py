import sys
import os
from unittest.mock import MagicMock
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ==========================================
# 核心修复：创建一个假的 QPlainTextEdit 类
# 不要用 MagicMock，否则继承时会拦截 __init__ 的赋值
# ==========================================
class FakeQPlainTextEdit:
    def __init__(self, parent=None): pass
    def setStyleSheet(self, *args): pass
    def moveCursor(self, *args): pass
    def insertPlainText(self, *args): pass
    def textCursor(self): return MagicMock()
    def closeEvent(self, *args): pass

# 伪造 PySide 模块
fake_pyside = ModuleType('PySide')
fake_qtgui = ModuleType('PySide.QtGui')
fake_qtcore = ModuleType('PySide.QtCore')

fake_qtgui.QPlainTextEdit = FakeQPlainTextEdit
fake_qtgui.QTextCursor = MagicMock()
fake_qtgui.QApplication = MagicMock()
fake_qtgui.QMessageBox = MagicMock()
fake_qtcore.Qt = MagicMock()

fake_pyside.QtGui = fake_qtgui
fake_pyside.QtCore = fake_qtcore

sys.modules['PySide'] = fake_pyside
sys.modules['PySide.QtGui'] = fake_qtgui
sys.modules['PySide.QtCore'] = fake_qtcore
sys.modules['FreeCAD'] = MagicMock()
sys.modules['FreeCADGui'] = MagicMock()
sys.modules['Part'] = MagicMock()
sys.modules['cq_mod3d'] = MagicMock()

import terminal

def test_terminal_execution_namespace():
    """测试终端执行代码时，是否正确注入了变量"""
    term = terminal.PythonTerminal()
    
    # 确保我们的 Fake 类没有污染 local_vars
    assert isinstance(term.local_vars, dict), "local_vars 必须是字典"
    
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
    """测试终端遇到错误时，是否会捕获并输出"""
    term = terminal.PythonTerminal()
    term.write = MagicMock()
    
    term.execute_code("print(1/0)")
    
    term.write.assert_called_once()
    assert "ZeroDivisionError" in term.write.call_args[0][0]
