import pytest
import sys
import os
import types
import glob
from unittest.mock import MagicMock

# ==========================================
# 动态探测 FreeCAD 路径（兼容 Windows/Linux）
# ==========================================
def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        possible_paths = [
            os.path.join(prefix, 'lib', 'freecad', 'lib'),
            os.path.join(prefix, 'lib', 'freecad', 'Mod'),
            os.path.join(prefix, 'lib'),
            os.path.join(prefix, 'lib', 'python3.11', 'site-packages'),
            os.path.join(prefix, 'Library', 'lib'),
            os.path.join(prefix, 'Library', 'bin'),
            os.path.join(prefix, 'Lib', 'site-packages'),
        ]
        for p in possible_paths:
            if os.path.exists(p) and p not in sys.path:
                sys.path.append(p)

    if sys.platform == 'win32':
        for p in glob.glob(r"C:\Program Files\FreeCAD*\bin"):
            if p not in sys.path: sys.path.append(p)

add_freecad_to_path()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 构建假 PySide 环境
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

if 'terminal' in sys.modules:
    del sys.modules['terminal']

try:
    import FreeCAD
    import Part
except ImportError as e:
    pytest.skip(f"Skipping tests: FreeCAD not found. {e}", allow_module_level=True)

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
    assert "SyntaxError" in term.write.call_args[0][0]
