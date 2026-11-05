import pytest
import FreeCAD
import Part
import mod3d

def test_noise_extreme_amplitude_validity():
    """测试极大振幅的噪声是否依然是合法的 Solid"""
    base = mod3d.sphere(10)
    # 正常振幅
    res_normal = mod3d.apply_noise(base, density=0.5, amplitude=1.0, seed=42)
    assert res_normal.shape.isValid()
    
    # 极端振幅（可能产生自交）
    res_extreme = mod3d.apply_noise(base, density=1.0, amplitude=5.0, seed=42)
    # 即使形变再奇怪，也必须是有效的拓扑
    assert res_extreme.shape.isValid(), "极端噪声导致生成了 Invalid Shape！"

def test_twist_validity():
    """测试纯 B-rep 扭转后生成的实体是否合法"""
    base = mod3d.cube(10)
    res = mod3d.brep_twist_z(base.shape, az=2.0, sections=30)
    assert res.isValid(), "B-rep 扭转生成了 Invalid Shape！"
