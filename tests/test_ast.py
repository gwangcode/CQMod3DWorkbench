import pytest
import sys
import os
import types
import glob
from unittest.mock import MagicMock

# def add_freecad_to_path():
#     if 'CONDA_PREFIX' in os.environ:
#         prefix = os.environ['CONDA_PREFIX']
#         for p in [os.path.join(prefix, 'lib', 'freecad', 'lib'), os.path.join(prefix, 'Library', 'lib'), os.path.join(prefix, 'lib')]:
#             if os.path.exists(p) and p not in sys.path: sys.path.append(p)

# add_freecad_to_path()
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
import Part
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
    root_obj = term._build_tree(shape1 + shape2, clean_doc)
    
    assert root_obj.TypeId == "Part::MultiFuse"

def test_build_tree_cut_and_noise(clean_doc):
    term = PythonTerminal()
    obj1 = clean_doc.addObject("Part::Box", "model_1")
    obj1.Shape = Part.makeBox(10, 10, 10)
    obj2 = clean_doc.addObject("Part::Sphere", "model_2")
    obj2.Shape = Part.makeSphere(8)
    
    shape1 = mod3d.Shape(obj1.Shape, doc_name="model_1")
    shape2 = mod3d.Shape(obj2.Shape, doc_name="model_2")
    root_obj = term._build_tree(mod3d.apply_noise(shape1 - shape2, seed=42), clean_doc)
    
    assert root_obj.TypeId == "Part::FeaturePython"
