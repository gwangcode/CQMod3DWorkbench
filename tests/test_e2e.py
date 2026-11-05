import pytest
import sys
import os
import types
from unittest.mock import MagicMock

# 假 PySide
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
from terminal import PythonTerminal

@pytest.fixture
def term():
    doc = FreeCAD.newDocument("E2ETest")
    FreeCAD.setActiveDocument("E2ETest")
    yield PythonTerminal()
    FreeCAD.closeDocument("E2ETest")

def test_e2e_terminal_execution(term):
    """测试在终端连续输入代码，验证树结构是否正确"""
    # 1. 重写 do_show 里的 QTimer 让它同步执行
    import terminal
    original_singleShot = terminal.QtCore.QTimer.singleShot
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()  # 立即执行
    
    try:
        # 输入第一行
        term.execute_code("cube(10)")
        assert FreeCAD.ActiveDocument.getObject("model_1") is not None
        
        # 输入第二行，此时 model_1 应该被隐藏，并生成一个 Cut 节点
        term.execute_code('part("model_1") - cylinder(2, 15)')
        
        doc = FreeCAD.ActiveDocument
        # 找到那个 Cut 节点
        cut_node = None
        for obj in doc.Objects:
            if obj.TypeId == "Part::Cut":
                cut_node = obj
                break
                
        assert cut_node is not None, "E2E 执行失败：未生成 Cut 节点"
        assert cut_node.Base.Name == "model_1"
        assert cut_node.Tool.Name.startswith("Cylinder")
        
        # 验证原模型被隐藏
        assert FreeCAD.ActiveDocument.getObject("model_1").ViewObject.Visibility is False
        
    finally:
        terminal.QtCore.QTimer.singleShot = original_singleShot
