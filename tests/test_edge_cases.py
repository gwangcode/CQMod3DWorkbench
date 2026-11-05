import pytest
import sys
import os
import types
import glob
from unittest.mock import MagicMock

def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        for p in [os.path.join(prefix, 'lib', 'freecad', 'lib'), os.path.join(prefix, 'Library', 'lib')]:
            if os.path.exists(p) and p not in sys.path: sys.path.append(p)

add_freecad_to_path()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

sys.modules.update({'PySide6': fake_pyside, 'PySide6.QtCore': fake_qtcore, 'PySide6.QtGui': fake_qtgui, 'PySide6.QtWidgets': fake_qtwidgets})

if 'terminal' in sys.modules: del sys.modules['terminal']

import FreeCAD
from terminal import PythonTerminal

@pytest.fixture
def term():
    return PythonTerminal()

def test_invalid_part_name(term):
    doc = FreeCAD.newDocument("EdgeTestDoc")
    try:
        with pytest.raises(ValueError) as exc_info:
            term._part_func("not_exist_model")
        assert "找不到名为 'not_exist_model' 的对象" in str(exc_info.value)
    finally:
        FreeCAD.closeDocument("EdgeTestDoc")

def test_execute_syntax_error(term):
    term.write = MagicMock()
    term.execute_code("cube(")
    term.write.assert_called_once()
    assert "SyntaxError" in term.write.call_args[0][0]
