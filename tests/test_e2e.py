import pytest
import sys
import os
import types
from unittest.mock import MagicMock

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
    doc = FreeCAD.newDocument("E2ETest")
    FreeCAD.setActiveDocument("E2ETest")
    yield PythonTerminal()
    FreeCAD.closeDocument("E2ETest")

def test_e2e_terminal_execution(term):
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    
    term.execute_code("cube(10)")
    
    doc = FreeCAD.ActiveDocument
    obj = doc.getObject("model_1")
    assert obj is not None, "E2E 执行失败：未生成 model_1 对象"
    assert obj.TypeId == "Part::Feature"
    assert obj.Shape.Volume > 0
    
    term.execute_code('part("model_1") - cylinder(2, 15)')
    
    cut_node = None
    for o in doc.Objects:
        if o.TypeId == "Part::Cut":
            cut_node = o
            break
            
    assert cut_node is not None, "E2E 执行失败：未生成 Cut 节点"
    assert cut_node.Base.Name == "model_1"
    
    model_1_obj = next((o for o in doc.Objects if o.Name == "model_1"), None)
    assert model_1_obj is not None, "E2E 执行失败：原来的 model_1 被意外删除！"
    
    if hasattr(model_1_obj, 'ViewObject') and model_1_obj.ViewObject is not None:
        assert model_1_obj.ViewObject.Visibility is False, "E2E 执行失败：原来的 model_1 未被隐藏"
