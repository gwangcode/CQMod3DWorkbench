import FreeCAD
import Part

def show(shape, name="Mod3D_Object"):
    """将形状直接显示在活动文档中。兼容 mod3d.Shape 和 Shape2d。"""
    from mod3d.patch import Shape
    from mod3d.shapes import Shape2d
    
    # 自动解包代理类和 2D 数据类
    if isinstance(shape, Shape):
        shape = shape.shape
    elif isinstance(shape, Shape2d):
        shape = shape.to_face()
        
    if not isinstance(shape, Part.Shape):
        FreeCAD.Console.PrintError("Input is not a Part.Shape!\n")
        return None
        
    doc = FreeCAD.ActiveDocument
    if not doc:
        docs = FreeCAD.listDocuments()
        doc = list(docs.values())[0] if docs else FreeCAD.newDocument()
            
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    doc.recompute()
    
    FreeCAD.Console.PrintMessage(f"✅ Created FreeCAD object: {name}\n")
    return obj
