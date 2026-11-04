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
    utils.show("Not a workplane")
    mock_freecad.Console.PrintError.assert_called_with("传入的对象不是 cq.Workplane！\n")

@patch('cadquery.exporters.export')
@patch('Part.Shape')
def test_show_valid_object(mock_part_shape, mock_cq_export, tmp_path):
    """测试传入正确的对象时，是否正确添加到 FreeCAD 文档"""
    mock_cq_obj = MagicMock()
    mock_cq_obj.val.return_value = MagicMock()
    
    # 伪造文档对象
    mock_doc = MagicMock()
    mock_freecad.ActiveDocument = mock_doc
    
    # 执行
    utils.show(mock_cq_obj, name="TestRock")
    
    # 验证
    mock_cq_export.assert_called_once()
    mock_doc.addObject.assert_called_once_with("Part::Feature", "TestRock")
    # 验证是否执行了 recompute
    mock_doc.recompute.assert_called_once()
