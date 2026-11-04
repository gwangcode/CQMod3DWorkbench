import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch

import utils
import InitGui

@patch('utils.FreeCAD')
def test_show_invalid_object(mock_freecad):
    """测试传入非 cq.Workplane 对象时，是否会安全退出"""
    utils.show("Not a workplane")
    mock_freecad.Console.PrintError.assert_called_with("传入的对象不是 cq.Workplane！\n")

@patch('utils.FreeCAD')
@patch('utils.Part')
@patch('cadquery.exporters.export')
def test_show_valid_object(mock_cq_export, mock_part, mock_freecad):
    """测试传入正确的对象时，是否正确添加到 FreeCAD 文档"""
    mock_cq_obj = MagicMock()
    mock_cq_obj.val.return_value = MagicMock()
    
    # 伪造文档对象，并让其判断为 True（有活动文档）
    mock_doc = MagicMock()
    mock_freecad.ActiveDocument = mock_doc
    
    # 执行
    utils.show(mock_cq_obj, name="TestRock")
    
    # 验证
    mock_cq_export.assert_called_once()
    mock_doc.addObject.assert_called_once_with("Part::Feature", "TestRock")
    mock_doc.recompute.assert_called_once()

def test_check_dependencies_missing():
    with patch.dict(sys.modules, {'cadquery': None, 'cq_mod3d': None}):
        assert InitGui.check_dependencies() is False

def test_check_dependencies_present():
    sys.modules['cadquery'] = MagicMock()
    sys.modules['cq_mod3d'] = MagicMock()
    assert InitGui.check_dependencies() is True
