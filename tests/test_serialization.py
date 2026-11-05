import pytest
import FreeCAD
import Part

def test_noise_feature_survives_save_and_reload(tmp_path):
    """测试自定义 FeaturePython 对象在保存并重新打开后能否正常重算"""
    from terminal import NoiseFeature, ViewProviderNoise
    
    doc = FreeCAD.newDocument("SerializationTest")
    FreeCAD.setActiveDocument("SerializationTest")
    
    # 1. 创建带 Noise 节点的模型
    base_obj = doc.addObject("Part::Sphere", "BaseSphere")
    base_obj.Radius = 10
    
    noise_obj = doc.addObject("Part::FeaturePython", "MyNoise")
    NoiseFeature(noise_obj)
    noise_obj.Base = base_obj
    noise_obj.Seed = 42
    noise_obj.Density = 0.5
    
    doc.recompute()
    original_volume = noise_obj.Shape.Volume
    assert original_volume > 0
    
    # 2. 保存文件
    file_path = str(tmp_path / "test_save.FCStd")
    doc.saveAs(file_path)
    FreeCAD.closeDocument("SerializationTest")
    
    # 3. 重新打开文件
    new_doc = FreeCAD.openDocument(file_path)
    FreeCAD.setActiveDocument(new_doc.Name)
    
    # 4. 验证对象是否完整恢复，并且可以再次重算
    reloaded_noise = new_doc.getObject("MyNoise")
    assert reloaded_noise is not None
    
    # 重新触发底层几何的变化，验证反序列化后的类是否还能接管计算
    new_doc.getObject("BaseSphere").Radius = 20
    new_doc.recompute()
    
    reloaded_volume = reloaded_noise.Shape.Volume
    assert reloaded_volume > original_volume, "重新打开后重算失败，可能是 onDocumentRestored 缺失或类映射断裂！"
    
    FreeCAD.closeDocument(new_doc.Name)
