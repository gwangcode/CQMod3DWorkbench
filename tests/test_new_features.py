import pytest
import sys
import os
import types
from unittest.mock import MagicMock, patch

def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        for p in [os.path.join(prefix, 'lib', 'freecad', 'lib'), os.path.join(prefix, 'Library', 'lib'), os.path.join(prefix, 'lib')]:
            if os.path.exists(p) and p not in sys.path: sys.path.append(p)
    if sys.platform == 'win32':
        import glob
        for p in glob.glob(r"C:\Program Files\FreeCAD*\bin"):
            if p not in sys.path: sys.path.append(p)

add_freecad_to_path()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
import terminal
from terminal import PythonTerminal

@pytest.fixture
def term():
    doc = FreeCAD.newDocument("TestDoc")
    FreeCAD.setActiveDocument("TestDoc")
    term = PythonTerminal()
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    yield term
    FreeCAD.closeDocument("TestDoc")

def test_bspline_surface_1d(term):
    pts = [(0,0,0), (10,0,0), (15,10,0), (10,20,0), (0,20,0), (-5,10,0)]
    term.execute_code(f"bspline_surface({pts})")
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None
    assert obj.Shape.ShapeType in ("Face", "Wire")
    assert obj.Shape.isValid()

def test_bspline_surface_2d(term):
    pts_2d = [
        [(0,0,0), (5,0,2), (10,0,0)],
        [(0,5,2), (5,5,5), (10,5,2)],
        [(0,10,0), (5,10,2), (10,10,0)]
    ]
    term.execute_code(f"bspline_surface({pts_2d})")
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None
    assert obj.Shape.isValid()

def test_runf(term, tmp_path):
    script_file = tmp_path / "my_script.py"
    script_file.write_text("show(cube(10), 'TestBox')\n")
    term.execute_code(f'runf(r"{script_file}")')
    obj = FreeCAD.ActiveDocument.getObject("TestBox")
    assert obj is not None
    assert abs(obj.Shape.Volume - 1000.0) < 1e-3

def test_2d_shape_display(term):
    term.execute_code("polygon(10)")
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None
    assert obj.Shape.ShapeType == "Face"

def test_clear_command(term):
    term._cleared = False
    term.clear = MagicMock()
    term.insertPlainText = MagicMock()
    term.execute_code("clear")
    term.clear.assert_called_once()
    term.insertPlainText.assert_called_once_with(">>> ")

def test_copy_selected_logic():
    import FreeCADGui
    
    if not hasattr(FreeCADGui, 'Workbench'):
        FreeCADGui.Workbench = type('Workbench', (object,), {})
    if not hasattr(FreeCADGui, 'addWorkbench'):
        FreeCADGui.addWorkbench = MagicMock()
    if not hasattr(FreeCADGui, 'Selection'):
        FreeCADGui.Selection = MagicMock()

    mock_obj = MagicMock()
    mock_obj.Name = "model_1"
    
    with patch('FreeCAD.Console.PrintMessage'), \
         patch('FreeCAD.Console.PrintError'), \
         patch('PySide6.QtWidgets.QApplication.clipboard') as mock_clipboard:
         
        from InitGui import Code3DWorkbench
        wb = Code3DWorkbench()
        wb.terminal = MagicMock()
        
        with patch.object(FreeCADGui.Selection, 'getSelection', return_value=[mock_obj]):
            wb._copy_selected_part()
            
        # 现在只断言剪贴板被调用，不再断言终端插入
        mock_clipboard.return_value.setText.assert_called_once_with('part("model_1")')
