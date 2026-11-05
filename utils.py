import FreeCAD
import Part

def show(shape, name="Mod3D_Object"):
    """
    将 FreeCAD Part.Shape 直接显示在活动的文档中。
    这是供终端内部及用户调用的底层显示函数。
    """
    if not isinstance(shape, Part.Shape):
        FreeCAD.Console.PrintError("Error: Input is not a valid Part.Shape!\n")
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
