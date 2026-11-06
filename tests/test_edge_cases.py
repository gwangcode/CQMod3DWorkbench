import pytest
import sys
import os
import types
from unittest.mock import MagicMock

class DummyQPlainTextEdit:
    NoWrap = 0
    def __init__(self, *args, **kwargs): pass
    def setStyleSheet(self, *args, **kwargs): pass
    def insertPlainText(self, *args, **kwargs): pass
    def moveCursor(self, *args, **kwargs): pass
    def textCursor(self): return MagicMock()
    def setLineWrapMode(self, mode): pass

fake_pyside = types.ModuleType("PySide6")
fake_qtcore = types.ModuleType("PySide6.QtCore")
fake_qtgui = types.ModuleType("PySide6.QtGui")
fake_qtwidgets = types.ModuleType("PySide6.QtWidgets")
fake_qtwidgets.QPlainTextEdit = DummyQPlainTextEdit
fake_qtwidgets.QApplication = MagicMock()
fake_qtcore.Qt = MagicMock()
fake_qtcore.QTimer = MagicMock()
fake_qtgui.QTextCursor = MagicMock()

sys.modules.update({'PySide6': fake_pyside, 'PySide6.QtCore': fake_qtcore, 'PySide6.QtGui': fake_qtgui, 'PySide6.QtWidgets': fake_qtwidgets})

if 'terminal' in sys.modules: del sys.modules['terminal']

import FreeCAD
import Part
import mod3d
from terminal import PythonTerminal

@pytest.fixture
def term():
    doc = FreeCAD.newDocument("EdgeTestDoc")
    FreeCAD.setActiveDocument("EdgeTestDoc")
    yield PythonTerminal()
    FreeCAD.closeDocument("EdgeTestDoc")

def test_invalid_part_name(term):
    with pytest.raises(ValueError) as exc_info:
        term._part_func("not_exist_model")
    # 断言英文报错
    assert "Could not find an object named 'not_exist_model'" in str(exc_info.value)

def test_invalid_operator_type():
    box = mod3d.cube(10)
    with pytest.raises(ValueError):
        box + "I am a string"

def test_execute_syntax_error(term):
    term.insertPlainText = MagicMock()
    term.write = MagicMock()
    term.execute_code("cube(")
    term.write.assert_called_once()
    # 断言英文报错
    assert "Syntax error" in term.write.call_args[0][0]
