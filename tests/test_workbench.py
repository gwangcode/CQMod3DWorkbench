import sys
import os

# 将项目根目录添加到 sys.path (解决 ModuleNotFoundError: No module named 'utils')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch

# ==========================================
# 核心打桩 (Mocking)：在导入任何代码前，
# 伪造 FreeCAD, Part 和 PySide 模块，防止无头环境崩溃
# ==========================================
mock_freecad = MagicMock()
mock_freecad_gui = MagicMock()
mock_part = MagicMock()
mock_pyside = MagicMock()
mock_qtgui = MagicMock()
mock_qtcore = MagicMock()

# 将它们注入 sys.modules
sys.modules['FreeCAD'] = mock_freecad
sys.modules['FreeCADGui'] = mock_freecad_gui
sys.modules['Part'] = mock_part
sys.modules['PySide'] = mock_pyside
sys.modules['PySide.QtGui'] = mock_qtgui
sys.modules['PySide.QtCore'] = mock_qtcore

# 伪造 cadquery 防止导入报错
sys.modules['cadquery'] = MagicMock()
sys.modules['cq_mod3d'] = MagicMock()

# 现在可以安全导入你的模块了
import utils
import InitGui


# ==========================================
# 1. 测试 utils.py 的 BREP 转换逻辑
# ==========================================
def test_show_invalid_object():
    """测试传入非 cq.Workplane 对象时，是否会安全退出"""
    with patch('FreeCAD.Console.PrintError') as mock_err:
        utils.show("Not a workplane")
        mock_err.assert_called_once()
        assert "不是 cq.Workplane" in mock_err.call_args[0][0]

@patch('cadquery.exporters.export')
@patch('Part.show')
def test_show_valid_object(mock_part_show, mock_cq_export, tmp_path):
    """测试传入正确的对象时，是否调用了导出和显示函数"""
    # 伪造一个 cq.Workplane 对象
    mock_cq_obj = MagicMock()
    mock_cq_obj.val.return_value = True
    
    # 伪造临时文件路径
    test_brep_path = str(tmp_path / "test.brep")
    with open(test_brep_path, "w") as f:
        f.write("dummy")

    # 强制让 tempfile 返回这个路径
    with patch('tempfile.NamedTemporaryFile') as mock_tmp:
        mock_tmp.return_value.name = test_brep_path
        
        # 执行
        utils.show(mock_cq_obj, name="TestRock")
        
        # 断言
        mock_cq_export.assert_called_once()
        mock_part_show.assert_called_once()
        # 断言临时文件被清理
        assert not os.path.exists(test_brep_path)


# ==========================================
# 2. 测试 InitGui.py 的依赖检查逻辑
# ==========================================
def test_check_dependencies_missing():
    """测试缺少依赖时，返回 False"""
    with patch.dict(sys.modules, {'cadquery': None, 'cq_mod3d': None}):
        assert InitGui.check_dependencies() is False

def test_check_dependencies_present():
    """测试依赖存在时，返回 True"""
    sys.modules['cadquery'] = MagicMock()
    sys.modules['cq_mod3d'] = MagicMock()
    assert InitGui.check_dependencies() is True


# ==========================================
# 3. 测试 terminal.py 的多行代码逻辑
# ==========================================
def test_terminal_multiline_logic():
    """测试终端能否正确判断多行代码是否完整"""
    import codeop
    
    # 简单的一行代码，应该是完整的
    assert codeop.compile_command("a = 1", "<input>", "exec") is not None
    
    # 冒号结尾（需要缩进），应该是不完整的
    assert codeop.compile_command("for i in range(3):", "<input>", "exec") is None
    
    # 完整的循环，应该是完整的
    assert codeop.compile_command("for i in range(3):\n    print(i)", "<input>", "exec") is not None
