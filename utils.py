import FreeCAD
import Part

def show(cq_obj, name="CQ_Object"):
    """将 CadQuery Workplane 对象转换为 FreeCAD 实体并显示在视图中。"""
    if not hasattr(cq_obj, "val"):
        print("传入的对象不是 cq.Workplane！")
        return
        
    # 不使用 try-except 吞错误，让异常直接抛出，方便 CI 排查
    import cadquery as cq
    
    # 直接获取 OCC 底层拓扑结构，绕过临时文件读写，速度最快且最稳定
    occ_shape = cq_obj.val().wrapped
    shape = Part.Shape(occ_shape)
    
    # 获取或创建文档
    doc = FreeCAD.ActiveDocument
    if not doc:
        doc = FreeCAD.newDocument()
        
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    doc.recompute()
    
    print(f"✅ 已生成 FreeCAD 对象: {name}")
