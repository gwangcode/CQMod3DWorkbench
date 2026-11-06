import pytest
import sys
import os
import types
from unittest.mock import MagicMock

# ==========================================
# 动态探测 FreeCAD 路径 (兼容 Windows/Linux)
# ==========================================
def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        for p in [os.path.join(prefix, 'lib', 'freecad', 'lib'), os.path.join(prefix, 'Library', 'lib'), os.path.join(prefix, 'lib')]:
            if os.path.exists(p) and p not in sys.path: sys.path.append(p)
    if sys.platform == 'win32':
        import glob
        for p in glob.glob(r"C:\Program Files\FreeCAD*\bin"):
            if p not in sys.path: sys.path.append(p)

add_freecad_to_path()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ==========================================
# 假 PySide 环境
# ==========================================
class DummyQPlainTextEdit:
    NoWrap = 0
    def __init__(self, *args, **kwargs): pass
    def setStyleSheet(self, *args, **kwargs): pass
    def insertPlainText(self, *args, **kwargs): pass
    def moveCursor(self, *args, **kwargs): pass
    def textCursor(self): return MagicMock()
    def setLineWrapMode(self, mode): pass
    def clear(self): self._cleared = True

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
    doc = FreeCAD.newDocument("TestDoc")
    FreeCAD.setActiveDocument("TestDoc")
    term = PythonTerminal()
    # Mock QTimer 让它同步执行
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    yield term
    FreeCAD.closeDocument("TestDoc")

# ==========================================
# 测试 1：B-Spline 曲面生成
# ==========================================
def test_bspline_surface_1d(term):
    """测试一维点集生成闭合 B-spline 曲面"""
    pts = [(0,0,0), (10,0,5), (15,10,0), (10,20,-5), (0,20,0), (-5,10,5)]
    
    term.execute_code(f"bspline_surface({pts})")
    
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "未成功生成 B-spline 曲面"
    assert obj.Shape.ShapeType == "Face", "生成的形状不是曲面"
    assert obj.Shape.isValid(), "生成的 B-spline 曲面无效"

def test_bspline_surface_2d(term):
    """测试二维点阵生成 B-spline 曲面"""
    pts_2d = [
        [(0,0,0), (5,0,2), (10,0,0)],
        [(0,5,2), (5,5,5), (10,5,2)],
        [(0,10,0), (5,10,2), (10,10,0)]
    ]
    
    term.execute_code(f"bspline_surface({pts_2d})")
    
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "未成功生成 B-spline 曲面"
    assert obj.Shape.isValid(), "生成的 B-spline 曲面无效"

# ==========================================
# 测试 2：runf 脚本执行功能
# ==========================================
def test_runf(term, tmp_path):
    """测试通过 runf 执行本地 Python 脚本"""
    # 创建一个临时脚本
    script_file = tmp_path / "my_script.py"
    script_file.write_text("show(cube(10), 'TestBox')\n")
    
    # 执行 runf
    term.execute_code(f'runf(r"{script_file}")')
    
    # 验证脚本中的代码是否被执行，生成了 TestBox
    obj = FreeCAD.ActiveDocument.getObject("TestBox")
    assert obj is not None, "runf 执行失败，未生成脚本中的对象"
    assert abs(obj.Shape.Volume - 1000.0) < 1e-3

# ==========================================
# 测试 3：2D 图形自动显示
# ==========================================
def test_2d_shape_display(term):
    """测试输入 2D 图元时，自动转为 Part.Face 并显示"""
    term.execute_code("polygon(10)")
    
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "未成功显示 2D 图形"
    assert obj.Shape.ShapeType == "Face", "2D 图形未转换为平面"

# ==========================================
# 测试 4：clear / cls 命令
# ==========================================
def test_clear_command(term):
    """测试 clear 命令是否能清空终端"""
    term._cleared = False
    term.clear = MagicMock()
    
    term.execute_code("clear")
    
    term.clear.assert_called_once()
    # 验证清屏后是否重新插入了提示符
    assert term.insertPlainText.call_args[0][0] == ">>> "

# ==========================================
# 测试 5：复制到剪贴板逻辑 (Ctrl+Shift+C)
# ==========================================
def test_copy_selected_logic():
    """测试 InitGui 中的复制方法逻辑"""
    # 由于 InitGui 强依赖 FreeCADGui，我们直接测试其核心逻辑
    import FreeCADGui
    from unittest.mock import patch
    
    # Mock FreeCADGui.Selection 返回一个选中的对象
    mock_obj = MagicMock()
    mock_obj.Name = "model_1"
    
    with patch('FreeCADGui.Selection.getSelection', return_value=[mock_obj]):
        with patch('PySide6.QtWidgets.QApplication.clipboard') as mock_clipboard:
            # 模拟 Workbench 实例
            from InitGui import Code3DWorkbench
            wb = Code3DWorkbench()
            wb.terminal = MagicMock()
            
            # 调用复制函数
            wb._copy_selected_part()
            
            # 断言剪贴板被写入了正确的代码
            mock_clipboard.return_value.setText.assert_called_once_with('part("model_1")')
            # 断言终端被插入了正确的代码
            wb.terminal.insertPlainText.assert_called_once_with('part("model_1")')
