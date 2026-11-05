import pytest
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 仅 Mock PySide，保留真实的 FreeCAD
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()

import FreeCAD
import Part
import mod3d
from terminal import PythonTerminal

@pytest.fixture
def term():
    return PythonTerminal()

def test_invalid_part_name(term):
    """测试查找不存在的对象时，是否抛出带有提示信息的 ValueError"""
    with pytest.raises(ValueError) as exc_info:
        term._part_func("not_exist_model")
    assert "找不到名为 'not_exist_model' 的对象" in str(exc_info.value)

def test_invalid_operator_type():
    """测试图元与非法类型相加时，是否抛出正确的 ValueError"""
    box = mod3d.cube(10)
    with pytest.raises(ValueError):
        box + "I am a string"
    with pytest.raises(ValueError):
        box - {"a": 1}

def test_execute_syntax_error(term):
    """测试终端输入语法错误的代码时，是否能捕获并打印错误，而不是让程序崩溃"""
    # 终端内部使用了 traceback 捕获
    term.insertPlainText = MagicMock()  # 防止写 UI
    term.write = MagicMock()
    
    # 执行一段语法错误的代码
    term.execute_code("cube(")
    
    # 确保捕获到了 SyntaxError 的 traceback
    term.write.assert_called_once()
    assert "SyntaxError" in term.write.call_args[0][0]
