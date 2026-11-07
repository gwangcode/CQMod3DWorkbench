import pytest
import sys
import os
import types
from unittest.mock import MagicMock
import numpy as np

# 动态探测 FreeCAD 路径
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
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    assert obj.Shape.ShapeType == "Face", "Coplanar points should generate a Face."
    assert obj.Shape.isValid(), "Generated Face is invalid."

# ==========================================
# 测试 2：稀疏点云 (生成极简面数的实体)
# ==========================================
def test_smooth_body_sparse_points(term):
    """Test sparse points (<30) generating a solid"""
    term.write = MagicMock()
    pts = [(0,0,0), (10,0,5), (15,10,-2), (10,20,8), (0,20,0), (-5,10,5)]
    
    term.execute_code(f"smooth_body({pts})")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    assert obj.Shape.ShapeType in ("Solid", "CompSolid"), "Should generate a 3D solid."
    assert obj.Shape.isValid(), "Generated solid is invalid."
    assert obj.Shape.Volume > 0, "Volume must be greater than 0."
    assert obj.Shape.isClosed(), "The resulting solid is not closed (leaking)."
    
    # 验证我们成功生成了“极简”的面片，而不是无数个碎三角面
    # 凸包切片放样，面数绝对不会超过 100 个
    assert len(obj.Shape.Faces) < 100, "Face count is too high, Loft may have failed and fell back to mesh."

# ==========================================
# 测试 3：密集点云 (Loft) 及 slices 参数验证
# ==========================================
def test_smooth_body_dense_points_and_slices(term):
    """Test dense points generating a solid via Section Loft, and verify slices parameter"""
    term.write = MagicMock()
    
    pts = []
    # 生成 49 个分布在椭球面上的点
    for i in range(7):
        for j in range(7):
            theta = np.pi * i / 6.0
            phi = 2 * np.pi * j / 6.0
            x = 10 * np.sin(theta) * np.cos(phi)
            y = 10 * np.sin(theta) * np.sin(phi)
            z = 15 * np.cos(theta)
            pts.append((x, y, z))
            
    # 1. 用极少的切片生成 (比如切 4 刀)
    term.execute_code(f"smooth_body({pts}, slices=4)")
    obj1 = FreeCAD.ActiveDocument.getObject("model_1")
    
    assert obj1 is not None, "Loft failed to generate object."
    faces_4 = len(obj1.Shape.Faces)
    
    FreeCAD.ActiveDocument.removeObject("model_1")
    
    # 2. 用更多的切片生成 (比如切 10 刀)
    term.execute_code(f"smooth_body({pts}, slices=10)")
    obj2 = FreeCAD.ActiveDocument.getObject("model_1")
    
    assert obj2 is not None, "Loft failed to generate object."
    faces_10 = len(obj2.Shape.Faces)
    
    assert obj2.Shape.isValid(), "Loft solid is invalid."
    assert obj2.Shape.isClosed(), "Loft solid is not closed."
    
    # 验证切片数越多，生成的 B-spline 曲面段数越多（面数越多）
    assert faces_10 > faces_4, "More slices should generate more surface patches."

# ==========================================
# 测试 4：点数不足时的异常处理
# ==========================================
def test_smooth_body_insufficient_points(term):
    """Test exception handling when there are fewer than 4 points"""
    term.write = MagicMock()
    term.execute_code("smooth_body([(0,0,0), (10,0,0), (0,10,0)])")
    
    term.write.assert_called_once()
    assert "At least 4 points are required" in term.write.call_args[0][0]
