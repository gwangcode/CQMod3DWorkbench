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
    return PythonTerminal()

def test_invalid_part_name(term):
    doc = FreeCAD.newDocument("EdgeTestDoc")
    FreeCAD.setActiveDocument("EdgeTestDoc")
    try:
        with pytest.raises(ValueError) as exc_info:
            term._part_func("not_exist_model")
        assert "找不到名为 'not_exist_model' 的对象" in str(exc_info.value)
    finally:
        FreeCAD.closeDocument("EdgeTestDoc")

def test_invalid_operator_type():
    box = mod3d.cube(10)
    with pytest.raises(ValueError):
        box + "I am a string"

def test_execute_syntax_error(term):
    term.insertPlainText = MagicMock()
    term.write = MagicMock()
    term.execute_code("cube(")
    term.write.assert_called_once()
    assert "语法错误" in term.write.call_args[0][0]
