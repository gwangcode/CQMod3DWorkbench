import pytest
import sys
import os
import glob
import numpy as np

# 动态挂载 FreeCAD 路径
def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        for p in [os.path.join(prefix, 'lib', 'freecad', 'lib'), os.path.join(prefix, 'lib', 'freecad', 'Mod'), os.path.join(prefix, 'lib')]:
            if os.path.exists(p) and p not in sys.path: sys.path.append(p)
    if sys.platform == 'win32':
        for p in glob.glob(r"C:\Program Files\FreeCAD*\bin"): 
            if p not in sys.path: sys.path.append(p)

add_freecad_to_path()
try:
    import FreeCAD
    import Part
except ImportError:
    pytest.skip("Skipping tests: FreeCAD not found.", allow_module_level=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import mod3d

def test_primitives_volume():
    """测试基础图元的体积计算准确性"""
    assert abs(mod3d.cube(10).Volume - 1000.0) < 1e-3
    assert abs(mod3d.cylinder(2, 10).Volume - (3.14159 * 4 * 10)) < 1.0

def test_operator_chain():
    """测试链式运算符：布尔、平移、旋转组合"""
    base = mod3d.cube(10)
    hole = mod3d.cylinder(2, 15)
    # 挖孔 -> 平移 -> 旋转
    res = (base - hole) + [5, 0, 0] @ [0, 0, 1.57]
    
    assert isinstance(res.shape, Part.Shape)
    assert res.Volume < 1000.0
    assert res.Volume > 0

def test_apply_noise_determinism():
    """测试相同随机种子的确定性，不同种子产生差异"""
    base = mod3d.sphere(10)
    res1 = mod3d.apply_noise(base, seed=42, amplitude=1.0)
    res2 = mod3d.apply_noise(base, seed=42, amplitude=1.0)
    res3 = mod3d.apply_noise(base, seed=99, amplitude=1.0)
    
    assert abs(res1.Volume - res2.Volume) < 1e-3  # 同种子体积一致
    assert abs(res1.Volume - res3.Volume) > 0.1   # 异种子体积不同
