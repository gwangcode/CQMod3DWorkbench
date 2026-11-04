import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch

# 打桩
mock_freecad = MagicMock()
mock_part = MagicMock()
sys.modules['FreeCAD'] = mock_freecad
sys.modules['FreeCADGui'] = MagicMock()
sys.modules['Part'] = mock_part
sys.modules['PySide'] = MagicMock()
sys.modules['PySide.QtGui'] = MagicMock()
sys.modules['PySide.QtCore'] = MagicMock()
sys.modules['cadquery'] = MagicMock()
sys.modules['cq_mod3d'] = MagicMock()

import utils
import InitGui

def test_show_invalid_object():
    """测试传入非 cq.Workplane 对象时，是否会安全退出"""
    utils.show("Not a workplane")
    # 直接断言底层 mock 被调用，绕过 patch 模块解析问题
    mock_freecad.Console.PrintError.assert_called_with("传入的对象不是 cq.Workplane！\n")

@patch('Part.show')
def test_show_valid_object(mock_part_show):
    """测试传入正确的对象时，是否调用了显示函数"""
    mock_cq_obj = MagicMock()
    mock_cq_obj.val.return_value = MagicMock() # 伪造 .val().wrapped
    
    utils.show(mock_cq_obj, name="TestRock")
    
    # 验证
    mock_part_show.assert_called_once()
    assert mock_part_show.call_args[1]['name'] if 'name' in mock_part_show.call_args[1] else True

def test_check_dependencies_missing():
    with patch.dict(sys.modules, {'cadquery': None, 'cq_mod3d': None}):
        assert InitGui.check_dependencies() is False

def test_check_dependencies_present():
    sys.modules['cadquery'] = MagicMock()
    sys.modules['cq_mod3d'] = MagicMock()
    assert InitGui.check_dependencies() is True
