import pytest
import sys
import os
import types
from unittest.mock import MagicMock

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
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    assert obj.Shape.ShapeType == "Face", "Coplanar points should generate a Face."
    assert obj.Shape.isValid(), "Generated Face is invalid."

# ==========================================
# 测试 2：非共面点集生成 3D 高阶自由曲面实体 (Loft 算法)
# ==========================================
def test_smooth_body_non_coplanar(term):
    """Test non-coplanar points generating a watertight 3D solid via Loft"""
    term.write = MagicMock()
    # A set of 3D points with significant Z-axis variation
    pts = [(0,0,0), (10,0,5), (15,10,-2), (10,20,8), (0,20,0), (-5,10,5), (5,5,15), (-5,-5,10)]
    
    # 使用默认的 15 层切片
    term.execute_code(f"smooth_body({pts})")
    
    if term.write.call_count > 0:
        print("\n=== TERMINAL ERROR ===")
        print(term.write.call_args[0][0])
        print("======================\n")
        
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    
    # 1. 验证它是实体 (Solid) 且有效 (Valid)
    assert obj.Shape.ShapeType in ("Solid", "CompSolid"), "Should generate a 3D solid."
    assert obj.Shape.isValid(), "Generated solid is invalid."
    
    # 2. 验证体积为正（没有被切破）
    assert obj.Shape.Volume > 0, "Volume must be greater than 0."
    
    # 3. 核心校验：验证 Loft 的“极简面数”特性
    # Loft 算法切片 15 次，通常只会生成十几个侧面，加上顶底两面
    # 面数绝对不应该超过 50，这证明了我们成功抛弃了微小的三角网格！
    assert len(obj.Shape.Faces) >= 2, "Loft should generate at least some faces."
    assert len(obj.Shape.Faces) < 50, "Face count is too high, Loft may have failed and fell back to mesh."
    
    # 4. 验证水密性（Watertight）：检查实体是否完全封闭
    assert obj.Shape.isClosed(), "The resulting solid is not closed (leaking)."

# ==========================================
# 测试 3：验证切片数量对 Loft 的影响
# ==========================================
def test_smooth_body_slices_parameter(term):
    """Test if changing the slices parameter correctly affects the topology"""
    term.write = MagicMock()
    # A tall point cloud
    pts = [(0,0,0), (10,0,5), (0,10,10), (-10,0,15), (0,-10,20), (0,0,25), (5,5,12), (-5,-5,8)]
    
    # 1. 用极少的切片生成
    term.execute_code(f"smooth_body({pts}, slices=5)")
    obj1 = FreeCAD.ActiveDocument.getObject("model_1")
    faces_5 = len(obj1.Shape.Faces)
    
    # 清理文档重新生成
    FreeCAD.ActiveDocument.removeObject("model_1")
    
    # 2. 用更多的切片生成
    term.execute_code(f"smooth_body({pts}, slices=20)")
    obj2 = FreeCAD.ActiveDocument.getObject("model_1")
    faces_20 = len(obj2.Shape.Faces)
    
    # 验证切片数越多，生成的 B-spline 曲面段数越多（面数越多）
    assert faces_20 > faces_5, "More slices should generate more surface patches."

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
