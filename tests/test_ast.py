import pytest
import sys
import os
import types
import glob
from unittest.mock import MagicMock

# ==========================================
# 【核心修复】动态探测 FreeCAD 路径（兼容 Windows/Linux）
# ==========================================
def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        # 添加所有可能的路径（Linux 和 Windows）
        possible_paths = [
            os.path.join(prefix, 'lib', 'freecad', 'lib'),
            os.path.join(prefix, 'lib', 'freecad', 'Mod'),
            os.path.join(prefix, 'lib'),
            os.path.join(prefix, 'lib', 'python3.11', 'site-packages'),
            os.path.join(prefix, 'Library', 'lib'),           # Windows
            os.path.join(prefix, 'Library', 'bin'),           # Windows
            os.path.join(prefix, 'Lib', 'site-packages'),     # Windows
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
def clean_doc():
    doc = FreeCAD.newDocument("TestDoc")
    FreeCAD.setActiveDocument("TestDoc")
    yield doc
    FreeCAD.closeDocument("TestDoc")

def test_build_tree_fusion(clean_doc):
    term = PythonTerminal()
    obj1 = clean_doc.addObject("Part::Box", "model_1")
    obj1.Shape = Part.makeBox(10, 10, 10)
    obj2 = clean_doc.addObject("Part::Sphere", "model_2")
    obj2.Shape = Part.makeSphere(5)
    
    shape1 = mod3d.Shape(obj1.Shape, doc_name="model_1")
    shape2 = mod3d.Shape(obj2.Shape, doc_name="model_2")
    ast_result = shape1 + shape2
    
    root_obj = term._build_tree(ast_result, clean_doc)
    assert root_obj.TypeId == "Part::MultiFuse"
    assert "model_1" in [o.Name for o in root_obj.Shapes]
    assert "model_2" in [o.Name for o in root_obj.Shapes]

def test_build_tree_cut_and_noise(clean_doc):
    term = PythonTerminal()
    obj1 = clean_doc.addObject("Part::Box", "model_1")
    obj1.Shape = Part.makeBox(10, 10, 10)
    obj2 = clean_doc.addObject("Part::Sphere", "model_2")
    obj2.Shape = Part.makeSphere(8)
    
    shape1 = mod3d.Shape(obj1.Shape, doc_name="model_1")
    shape2 = mod3d.Shape(obj2.Shape, doc_name="model_2")
    
    cut_ast = shape1 - shape2
    noise_ast = mod3d.apply_noise(cut_ast, seed=42)
    
    root_obj = term._build_tree(noise_ast, clean_doc)
    assert root_obj.TypeId == "Part::FeaturePython"
    assert root_obj.Name.startswith("Noise")
    base_obj = root_obj.Base
    assert base_obj.TypeId == "Part::Cut"
    assert base_obj.Base.Name == "model_1"
    assert base_obj.Tool.Name == "model_2"
