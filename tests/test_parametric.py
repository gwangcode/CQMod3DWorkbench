import pytest
import sys
import os
import glob

# ==========================================
# 动态探测 FreeCAD 路径（兼容 Windows/Linux）
# ==========================================
def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        possible_paths = [
            os.path.join(prefix, 'lib', 'freecad', 'lib'),
            os.path.join(prefix, 'lib', 'freecad', 'Mod'),
            os.path.join(prefix, 'lib'),
            os.path.join(prefix, 'lib', 'python3.11', 'site-packages'),
            os.path.join(prefix, 'Library', 'lib'),
            os.path.join(prefix, 'Library', 'bin'),
            os.path.join(prefix, 'Lib', 'site-packages'),
        ]
        for p in possible_paths:
            if os.path.exists(p) and p not in sys.path:
                sys.path.append(p)

    if sys.platform == 'win32':
        for p in glob.glob(r"C:\Program Files\FreeCAD*\bin"):
            if p not in sys.path: sys.path.append(p)

add_freecad_to_path()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import FreeCAD
    import Part
except ImportError as e:
    pytest.skip(f"Skipping tests: FreeCAD not found. {e}", allow_module_level=True)

import mod3d

def test_parametric_noise_recompute():
    """验证修改 Seed 或底层 Radius 时能重新计算"""
    from terminal import NoiseFeature

    doc = FreeCAD.newDocument("ParamTest")
    try:
        base_obj = doc.addObject("Part::Sphere", "BaseSphere")
        base_obj.Radius = 10
        
        noise_obj = doc.addObject("Part::FeaturePython", "MyNoise")
        NoiseFeature(noise_obj)
        noise_obj.Base = base_obj
        noise_obj.Seed = 42
        noise_obj.Density = 0.5
        noise_obj.Amplitude = 1.0
        
        doc.recompute()
        vol1 = noise_obj.Shape.Volume
        assert vol1 > 0
        
        base_obj.Radius = 20
        doc.recompute()
        vol2 = noise_obj.Shape.Volume
        assert vol2 > vol1
        
        noise_obj.Seed = 99
        doc.recompute()
        vol3 = noise_obj.Shape.Volume
        assert abs(vol3 - vol2) > 0.1
    finally:
        FreeCAD.closeDocument("ParamTest")
