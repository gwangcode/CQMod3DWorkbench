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

def test_e2e_terminal_execution(term, mocker):
    """测试在终端连续输入代码，验证是否正确触发了显示逻辑"""
    
    # 1. Mock 掉 QTimer，让其立即执行
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    
    # 2. Mock 掉 show 函数，避免真实创建文档对象的复杂性
    mock_show = mocker.patch('terminal.show')
    mock_show.return_value = MagicMock()
    
    # 3. 模拟输入第一行: cube(10)
    term.execute_code("cube(10)")
    
    # 验证 show 被调用了一次，且名字是 model_1
    mock_show.assert_called_once()
    args, kwargs = mock_show.call_args
    assert kwargs.get('name') == "model_1"
    assert isinstance(args[0], Part.Shape)
    
    mock_show.reset_mock()
    
    # 4. 模拟输入第二行: part("model_1") - cylinder(2, 15)
    # 因为 show 被 mock 了，文档里实际上没有 model_1，我们需要伪造一个
    doc = FreeCAD.ActiveDocument
    fake_base = doc.addObject("Part::Box", "model_1")
    fake_base.Shape = Part.makeBox(10,10,10)
    
    term.execute_code('part("model_1") - cylinder(2, 15)')
    
    # 因为这是布尔运算，应该走到 _build_tree，而不是直接调用 show
    # 所以 mock_show 不应该被调用（终端内部调用的是 _build_tree 里的 doc.addObject）
    mock_show.assert_not_called()
    
    # 验证文档中是否生成了 Cut 节点
    cut_node = None
    for obj in doc.Objects:
        if obj.TypeId == "Part::Cut":
            cut_node = obj
            break
            
    assert cut_node is not None, "E2E 执行失败：未生成 Cut 节点"
    assert cut_node.Base.Name == "model_1"
