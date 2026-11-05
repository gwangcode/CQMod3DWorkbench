import pytest
import sys
import os
import types
from unittest.mock import MagicMock

# 假 PySide 环境
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
import terminal
from terminal import PythonTerminal

@pytest.fixture
def term():
    doc = FreeCAD.newDocument("E2ETest")
    FreeCAD.setActiveDocument("E2ETest")
    yield PythonTerminal()
    FreeCAD.closeDocument("E2ETest")

def test_e2e_terminal_execution(term):
    """测试在终端连续输入代码，验证是否真实生成了 FreeCAD 节点"""
    
    # 1. Mock QTimer，让它同步执行，避免异步问题
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    
    # 2. 输入第一行: cube(10)
    term.execute_code("cube(10)")
    
    # 验证 FreeCAD 文档中是否真实生成了 model_1
    doc = FreeCAD.ActiveDocument
    obj = doc.getObject("model_1")
    assert obj is not None, "E2E 执行失败：未生成 model_1 对象"
    assert obj.TypeId == "Part::Feature"
    assert obj.Shape.Volume > 0
    
    # 3. 输入第二行: part("model_1") - cylinder(2, 15)
    term.execute_code('part("model_1") - cylinder(2, 15)')
    
    # 验证文档中是否生成了 Cut 节点
    cut_node = None
    for o in doc.Objects:
        if o.TypeId == "Part::Cut":
            cut_node = o
            break
            
    assert cut_node is not None, "E2E 执行失败：未生成 Cut 节点"
    assert cut_node.Base.Name == "model_1"
    
    # 验证原来的 model_1 被隐藏（非破坏性建模）
    assert doc.getObject("model_1").ViewObject.Visibility is False
