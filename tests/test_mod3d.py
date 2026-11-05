import pytest
import sys
import os
import glob

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
    box = mod3d.cube(10)
    assert isinstance(box.shape, Part.Shape)
    assert abs(box.Volume - 1000.0) < 1e-3

def test_mod3d_operator_patch():
    box = mod3d.cube(10)
    moved = box + [10, 0, 0]
    assert abs(moved.BoundBox.XMin - 10.0) < 1e-3
    
    sphere = mod3d.sphere(6)
    cut_shape = box - sphere
    assert cut_shape.Volume < box.Volume

def test_apply_noise_seed_determinism():
    """测试相同的 Seed 是否产生完全一致的结果"""
    base = mod3d.sphere(10)
    res1 = mod3d.apply_noise(base, density=0.5, amplitude=1.0, seed=42)
    res2 = mod3d.apply_noise(base, density=0.5, amplitude=1.0, seed=42)
    
    # 比较两者的包围盒（或顶点数据），如果 Seed 生效，两者的几何特征应完全一样
    assert abs(res1.BoundBox.XMax - res2.BoundBox.XMax) < 1e-5
    assert abs(res1.Volume - res2.Volume) < 1e-3

def test_apply_noise_seed_difference():
    """测试不同的 Seed 是否产生不同的结果"""
    base = mod3d.sphere(10)
    res1 = mod3d.apply_noise(base, density=0.5, amplitude=1.0, seed=42)
    res2 = mod3d.apply_noise(base, density=0.5, amplitude=1.0, seed=99)
    
    # 两个模型的体积或包围盒应该有区别
    assert abs(res1.Volume - res2.Volume) > 0.1
