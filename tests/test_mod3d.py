import pytest
import sys
import os
import glob

# --- 动态探测 FreeCAD 的路径并加入 sys.path ---
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
    pytest.skip(f"Skipping tests: FreeCAD not found. {e}", allow_module_level=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mod3d

def test_mod3d_primitives():
    """测试原生的图元生成"""
    box = mod3d.cube(10)
    assert isinstance(box.shape, Part.Shape)
    assert abs(box.Volume - 1000.0) < 1e-3
    
    sph = mod3d.sphere(5)
    assert isinstance(sph.shape, Part.Shape)
    # 体积约 523.6
    assert abs(sph.Volume - (4/3 * 3.14159 * 125)) < 1.0

def test_mod3d_operator_patch():
    """测试打上补丁后的运算符重载"""
    # FreeCAD 原生 makeBox 从原点 (0,0,0) 开始
    box = mod3d.cube(10)
    
    # 测试平移 (+ [x, y, z])
    # 平移 10 后，X 范围应该是 10 ~ 20
    moved = box + [10, 0, 0]
    assert abs(moved.BoundBox.XMin - 10.0) < 1e-3
    assert abs(moved.BoundBox.XMax - 20.0) < 1e-3
    
    # 测试布尔差集 (shape - shape)
    sphere = mod3d.sphere(6)
    cut_shape = box - sphere
    assert cut_shape.Volume < box.Volume
    
    # 测试旋转 (@ [rx, ry, rz]) 围绕原点旋转 90 度
    rotated = box @ [0, 0, 1.5708]
    assert isinstance(rotated.shape, Part.Shape)
    # 确保旋转后包围盒发生改变
    assert abs(rotated.BoundBox.XMin - (-10.0)) < 1e-2
