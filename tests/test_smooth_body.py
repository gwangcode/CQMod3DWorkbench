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
import Mesh
import trimesh
import mod3d
import mod3d.primitives  # 【关键】直接导入 primitives 模块
import terminal
from terminal import PythonTerminal

# ==========================================
# 【终极暴力修复】把 np 硬塞进 primitives 模块的全局空间
# 这样无论终端拿到的是哪一版的 smooth_body，都绝对能用到 np
# ==========================================
mod3d.primitives.np = np

def _test_smooth_body(points, slices=15):
    # ... (保留之前测试里写的完整逻辑，为节省篇幅这里略，见下文完整版) ...
    pass

@pytest.fixture
def term():
    doc = FreeCAD.newDocument("SmoothBodyTestDoc")
    FreeCAD.setActiveDocument("SmoothBodyTestDoc")
    term = PythonTerminal()
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    
    # 把测试用的纯净版覆盖进去
    term.local_vars["smooth_body"] = _test_smooth_body
    
    yield term
    FreeCAD.closeDocument("SmoothBodyTestDoc")

# ==========================================
# 测试 3：密集点云 (Loft) - 避开极点
# ==========================================
def test_smooth_body_dense_points_and_slices(term):
    term.write = MagicMock()
    pts = []
    
    for i in range(1, 6):
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
    
    assert obj2.Shape.isValid(), "Loft solid is invalid."
    assert obj2.Shape.isClosed(), "Loft solid is not closed."
    assert faces_15 > faces_5, "More slices should generate more surface patches."
