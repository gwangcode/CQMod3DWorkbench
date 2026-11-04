import sys
import os
import glob
import pytest

# --- 动态探测 FreeCAD 的路径并加入 sys.path ---
def add_freecad_to_path():
    # 1. 针对 Linux / macOS 的 Conda 环境
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        possible_paths = [
            os.path.join(prefix, 'lib', 'freecad', 'lib'),
            os.path.join(prefix, 'lib', 'freecad', 'Mod'),
            os.path.join(prefix, 'lib'),
            os.path.join(prefix, 'lib', 'python3.11', 'site-packages'),
        ]
        for p in possible_paths:
            if os.path.exists(p) and p not in sys.path:
                sys.path.append(p)
    
    # 2. 针对 Windows 本地开发环境
    if sys.platform == 'win32':
        possible_win_paths = glob.glob(r"C:\Program Files\FreeCAD*\bin")
        possible_win_paths += glob.glob(r"C:\Program Files\FreeCAD*\lib")
        for p in possible_win_paths:
            if os.path.exists(p) and p not in sys.path:
                sys.path.append(p)

add_freecad_to_path()

# 尝试导入，如果还是找不到，就优雅地跳过这个测试文件
try:
    import FreeCAD
    import Part
except ImportError as e:
    pytest.skip(f"Skipping integration tests: FreeCAD not found. {e}", allow_module_level=True)

import cadquery as cq

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils

def test_real_geometry_conversion():
    """真实测试：CadQuery 导出 BREP -> FreeCAD 读取 -> 验证体积"""
    box = cq.Workplane("XY").box(10, 10, 10)
    
    doc = FreeCAD.newDocument("TestDoc")
    utils.show(box, name="RealBox")
    
    obj = doc.getObject("RealBox")
    assert obj is not None, "FreeCAD 中没有找到生成的对象"
    
    vol = obj.Shape.Volume
    assert abs(vol - 1000.0) < 1e-3, f"生成的几何体体积错误: {vol}"
    
    FreeCAD.closeDocument("TestDoc")
