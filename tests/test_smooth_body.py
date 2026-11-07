import pytest
import sys
import os
import types
from unittest.mock import MagicMock
import numpy as np

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
    # Mock QTimer 让它同步执行，避免异步问题
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
# 测试 2：稀疏点云 (触发引擎 A - B-Spline 拟合)
# ==========================================
def test_smooth_body_sparse_points(term):
    """Test sparse points (<30) generating a solid via B-Spline fitting"""
    term.write = MagicMock()
    pts = [(0,0,0), (10,0,5), (15,10,-2), (10,20,8), (0,20,0), (-5,10,5)]
    
    term.execute_code(f"smooth_body({pts})")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    assert obj.Shape.ShapeType in ("Solid", "CompSolid"), "Should generate a 3D solid."
    assert obj.Shape.isValid(), "Generated solid is invalid."
    assert obj.Shape.Volume > 0, "Volume must be greater than 0."
    assert obj.Shape.isClosed(), "The resulting solid is not closed (leaking)."
    
    # 因为是拟合出来的曲面加厚，面数虽然比原始凸包多，但不应像网格细分那么多
    assert len(obj.Shape.Faces) < 1000, "Face count is too high, B-Spline fitting may have failed."

# ==========================================
# 测试 3：密集点云 (触发引擎 B - Loft 切片) 及参数验证
# ==========================================
def test_smooth_body_dense_points_and_slices(term):
    """Test dense points (>=30) generating a solid via Loft, and verify slices parameter"""
    term.write = MagicMock()
    
    # 生成 49 个分布在椭球面上的点 (模拟石头)
    pts = []
    for i in range(7):
        for j in range(7):
            theta = np.pi * i / 6.0
            phi = 2 * np.pi * j / 6.0
            x = 10 * np.sin(theta) * np.cos(phi)
            y = 10 * np.sin(theta) * np.sin(phi)
            z = 15 * np.cos(theta)
            pts.append((x, y, z))
            
    # 1. 用极少的切片生成
    term.execute_code(f"smooth_body({pts}, slices=5)")
    obj1 = FreeCAD.ActiveDocument.getObject("model_1")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR (Slices=5) ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    assert obj1 is not None, "Loft failed to generate object."
    faces_5 = len(obj1.Shape.Faces)
    
    # 清理文档重新生成
    FreeCAD.ActiveDocument.removeObject("model_1")
    term.write.reset_mock()
    
    # 2. 用更多的切片生成
    term.execute_code(f"smooth_body({pts}, slices=15)")
    obj2 = FreeCAD.ActiveDocument.getObject("model_1")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR (Slices=15) ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    assert obj2 is not None, "Loft failed to generate object."
    faces_15 = len(obj2.Shape.Faces)
    
    # 验证 Loft 算法生效且面数极少
    assert obj2.Shape.isValid(), "Loft solid is invalid."
    assert obj2.Shape.isClosed(), "Loft solid is not closed."
    assert obj2.Shape.Volume > 0, "Volume must be greater than 0."
    
    # 验证切片数越多，生成的 B-spline 曲面段数越多（面数越多）
    assert faces_15 > faces_5, "More slices should generate more surface patches."

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
