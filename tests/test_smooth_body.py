import pytest
import sys
import os
import types
from unittest.mock import MagicMock

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
    doc = FreeCAD.newDocument("SmoothBodyTestDoc")
    FreeCAD.setActiveDocument("SmoothBodyTestDoc")
    term = PythonTerminal()
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    yield term
    FreeCAD.closeDocument("SmoothBodyTestDoc")

def test_smooth_body_coplanar(term):
    """测试共面点集生成 2D 曲面"""
    term.write = MagicMock()  # 【新增】Mock 以捕获错误
    pts = [(0,0,0), (10,0,0), (15,10,0), (10,20,0), (0,20,0), (-5,10,0)]
    
    term.execute_code(f"smooth_body({pts})")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "未成功生成对象"
    assert obj.Shape.ShapeType == "Face", "共面点应生成平面(Face)"
    assert obj.Shape.isValid(), "生成的面无效"

def test_smooth_body_non_coplanar(term):
    """测试非共面点集生成 3D 平滑实体"""
    term.write = MagicMock()
    pts = [(0,0,0), (10,0,5), (15,10,-2), (10,20,8), (0,20,0), (-5,10,5)]
    
    term.execute_code(f"smooth_body({pts})")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "未成功生成对象"
    assert obj.Shape.ShapeType in ("Solid", "CompSolid"), "非共面点应生成三维实体"
    assert obj.Shape.Volume > 0, "生成的实体体积必须大于 0"
    assert obj.Shape.isValid(), "生成的平滑实体无效"

def test_smooth_body_insufficient_points(term):
    """测试点数不足时的异常处理"""
    term.write = MagicMock()
    term.execute_code("smooth_body([(0,0,0), (10,0,0), (0,10,0)])")
    
    term.write.assert_called_once()
    assert "At least 4 points are required" in term.write.call_args[0][0]
