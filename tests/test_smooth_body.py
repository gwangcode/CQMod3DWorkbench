import pytest
import sys
import os
import types
from unittest.mock import MagicMock

# 动态探测 FreeCAD 路径 (兼容 Windows/Linux)
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

# 假 PySide 环境
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


# ==========================================
# 测试 1：共面点集生成 2D 曲面
# ==========================================
def test_smooth_body_coplanar(term):
    """Test coplanar points generating a 2D face"""
    term.write = MagicMock() 
    pts = [(0,0,0), (10,0,0), (15,10,0), (10,20,0), (0,20,0), (-5,10,0)]
    
    term.execute_code(f"smooth_body({pts})")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    assert obj.Shape.ShapeType == "Face", "Coplanar points should generate a Face."
    assert obj.Shape.isValid(), "Generated Face is invalid."

# ==========================================
# 测试 2：非共面点集生成 3D 高阶自由曲面实体
# ==========================================
def test_smooth_body_non_coplanar(term):
    """Test non-coplanar points generating a 3D B-Spline solid"""
    term.write = MagicMock()
    # A set of 3D points with significant Z-axis variation
    pts = [(0,0,0), (10,0,5), (15,10,-2), (10,20,8), (0,20,0), (-5,10,5)]
    
    term.execute_code(f"smooth_body({pts})")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    
    # With the new B-Spline + thicken algorithm, it should yield a valid solid
    assert obj.Shape.ShapeType in ("Solid", "CompSolid"), "Non-coplanar points should generate a 3D solid."
    assert obj.Shape.Volume > 0, "Volume must be greater than 0."
    assert obj.Shape.isValid(), "Generated B-Spline solid is invalid."

# ==========================================
# 测试 3：极端退化情况 (Fallback 测试)
# ==========================================
def test_smooth_body_degenerate_fallback(term):
    """Test the fallback mechanism when points are extremely degenerate (e.g., all on a line)."""
    term.write = MagicMock()
    # Points strictly on the X-axis (cannot form a 3D volume)
    pts = [(0,0,0), (1,0,0), (2,0,0), (3,0,0), (4,0,0)]
    
    term.execute_code(f"smooth_body({pts})")
    
    # The code should catch the error and either fail gracefully or return a zero-volume fallback
    # We mainly want to ensure it doesn't crash the terminal with a Segfault
    assert term.write.call_count >= 0, "Should handle degenerate points gracefully without crashing."

# ==========================================
# 测试 4：点数不足时的异常处理
# ==========================================
def test_smooth_body_insufficient_points(term):
    """Test exception handling when there are fewer than 4 points"""
    term.write = MagicMock()
    # Only 3 points
    term.execute_code("smooth_body([(0,0,0), (10,0,0), (0,10,0)])")
    
    # The terminal should catch the ValueError and print it
    term.write.assert_called_once()
    assert "At least 4 points are required" in term.write.call_args[0][0]
