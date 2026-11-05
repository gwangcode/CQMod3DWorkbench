import pytest
import sys
import os
import glob
import numpy as np

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
    assert abs(mod3d.cube(10).Volume - 1000.0) < 1e-3
    assert abs(mod3d.cylinder(2, 10).Volume - (3.14159 * 4 * 10)) < 1.0

def test_operator_chain():
    """测试链式运算符：注意运算优先级，需加上括号"""
    base = mod3d.cube(10)
    hole = mod3d.cylinder(2, 15)
    # 【核心修复】使用括号改变优先级
    res = ((base - hole) + [5, 0, 0]) @ [0, 0, 1.57]
    
    assert isinstance(res.shape, Part.Shape)
    assert res.Volume < 1000.0
    assert res.Volume > 0

def test_apply_noise_determinism():
    base = mod3d.sphere(10)
    res1 = mod3d.apply_noise(base, seed=42, amplitude=1.0)
    res2 = mod3d.apply_noise(base, seed=42, amplitude=1.0)
    res3 = mod3d.apply_noise(base, seed=99, amplitude=1.0)
    
    assert abs(res1.Volume - res2.Volume) < 1e-3
    assert abs(res1.Volume - res3.Volume) > 0.1
