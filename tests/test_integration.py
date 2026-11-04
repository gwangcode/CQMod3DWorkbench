import sys
import os
import glob
import pytest

def add_freecad_to_path():
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
    
    if sys.platform == 'win32':
        possible_win_paths = glob.glob(r"C:\Program Files\FreeCAD*\bin")
        possible_win_paths += glob.glob(r"C:\Program Files\FreeCAD*\lib")
        for p in possible_win_paths:
            if os.path.exists(p) and p not in sys.path:
                sys.path.append(p)

add_freecad_to_path()

try:
    import FreeCAD
    import Part
except ImportError as e:
    pytest.skip(f"Skipping integration tests: FreeCAD not found. {e}", allow_module_level=True)

import cadquery as cq
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils

def test_real_geometry_conversion():
    """真实测试：CadQuery -> FreeCAD 转换 -> 验证体积"""
    box = cq.Workplane("XY").box(10, 10, 10)
    
    doc = FreeCAD.newDocument("TestDoc")
    FreeCAD.setActiveDocument("TestDoc")
    
    utils.show(box, name="RealBox")
    
    # 直接从 ActiveDocument 获取对象，防止活动文档漂移
    obj = FreeCAD.ActiveDocument.getObject("RealBox")
    assert obj is not None, "FreeCAD 中没有找到生成的对象"
    
    vol = obj.Shape.Volume
    assert abs(vol - 1000.0) < 1e-3, f"生成的几何体体积错误: {vol}"
    
    FreeCAD.closeDocument("TestDoc")
