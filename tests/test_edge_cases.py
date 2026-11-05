import pytest
import sys
import os
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ==========================================
# 构建假 PySide 环境（保持原有逻辑）
# ==========================================
class DummyQPlainTextEdit:
    def __init__(self, *args, **kwargs): pass
    def setStyleSheet(self, *args, **kwargs): pass
    def insertPlainText(self, *args, **kwargs): pass
    def moveCursor(self, *args, **kwargs): pass
    def textCursor(self): return MagicMock()

fake_pyside = types.ModuleType("PySide6")
fake_qtcore = types.ModuleType("PySide6.QtCore")
fake_qtgui = types.ModuleType("PySide6.QtGui")
fake_qtwidgets = types.ModuleType("PySide6.QtWidgets")

fake_qtwidgets.QPlainTextEdit = DummyQPlainTextEdit
fake_qtwidgets.QApplication = MagicMock()
fake_qtcore.Qt = MagicMock()
fake_qtcore.QTimer = MagicMock()
fake_qtgui.QTextCursor = MagicMock()

fake_pyside.QtCore = fake_qtcore
fake_pyside.QtGui = fake_qtgui
fake_pyside.QtWidgets = fake_qtwidgets

sys.modules['PySide6'] = fake_pyside
sys.modules['PySide6.QtCore'] = fake_qtcore
sys.modules['PySide6.QtGui'] = fake_qtgui
sys.modules['PySide6.QtWidgets'] = fake_qtwidgets

# 强制清理缓存
if 'terminal' in sys.modules:
    del sys.modules['terminal']

import FreeCAD
import Part
import mod3d
from terminal import PythonTerminal

@pytest.fixture
def term():
    return PythonTerminal()

def test_invalid_part_name(term):
    """测试查找不存在的对象时，是否抛出带有提示信息的 ValueError"""
    # 【核心修复】创建一个活动文档，让代码能走到后续逻辑
    doc = FreeCAD.newDocument("EdgeTestDoc")
    FreeCAD.setActiveDocument("EdgeTestDoc")
    
    try:
        with pytest.raises(ValueError) as exc_info:
            term._part_func("not_exist_model")
        assert "找不到名为 'not_exist_model' 的对象" in str(exc_info.value)
    finally:
        FreeCAD.closeDocument("EdgeTestDoc")

def test_invalid_operator_type():
    """测试图元与非法类型相加时，是否抛出正确的 ValueError"""
    box = mod3d.cube(10)
    with pytest.raises(ValueError):
        box + "I am a string"

def test_execute_syntax_error(term):
    """测试终端输入语法错误的代码时，是否能捕获并打印错误，而不是让程序崩溃"""
    term.insertPlainText = MagicMock()
    term.write = MagicMock()
    
    # 执行一段语法错误的代码
    term.execute_code("cube(")
    
    # 确保捕获到了 SyntaxError 的 traceback
    term.write.assert_called_once()
    assert "SyntaxError" in term.write.call_args[0][0]
