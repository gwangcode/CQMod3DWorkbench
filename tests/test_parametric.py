import pytest
import FreeCAD
import Part

def test_parametric_noise_recompute(clean_doc=None):
    """验证修改 Seed 或底层 Radius 时能重新计算"""
    from terminal import NoiseFeature
    import mod3d

    # 创建基础模型
    doc = FreeCAD.newDocument("ParamTest")
    base_obj = doc.addObject("Part::Sphere", "BaseSphere")
    base_obj.Radius = 10
    
    # 创建噪声特征
    noise_obj = doc.addObject("Part::FeaturePython", "MyNoise")
    NoiseFeature(noise_obj)
    noise_obj.Base = base_obj
    noise_obj.Seed = 42
    noise_obj.Density = 0.5
    noise_obj.Amplitude = 1.0
    
    # 强制触发首次计算
    doc.recompute()
    vol1 = noise_obj.Shape.Volume
    assert vol1 > 0
    
    # 1. 修改底层 Base 半径，触发 Cascade 更新
    base_obj.Radius = 20
    doc.recompute()
    vol2 = noise_obj.Shape.Volume
    assert vol2 > vol1  # 半径变大，体积应变大
    
    # 2. 修改 Seed
    noise_obj.Seed = 99
    doc.recompute()
    vol3 = noise_obj.Shape.Volume
    assert abs(vol3 - vol2) > 0.1  # 种子变了，结果必须变
    
    FreeCAD.closeDocument("ParamTest")
