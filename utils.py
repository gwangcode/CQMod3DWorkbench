import FreeCAD
import Part

def show(shape, name="Mod3D_Object"):
    """直接将 FreeCAD Part.Shape 显示在文档中"""
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
