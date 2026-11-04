import FreeCAD
import Part

def show(cq_obj, name="CQ_Object"):
    if not hasattr(cq_obj, "val"):
        FreeCAD.Console.PrintError("Input is not a cq.Workplane!\n")
        return
    try:
        shape = Part.Shape(cq_obj.val().wrapped)
        doc = FreeCAD.ActiveDocument
        if not doc:
            docs = FreeCAD.listDocuments()
            doc = list(docs.values())[0] if docs else FreeCAD.newDocument()
                
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        doc.recompute()
        FreeCAD.Console.PrintMessage(f"✅ Created FreeCAD object: {name}\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"❌ Creation failed: {str(e)}\n")
