import os
import FreeCAD
import Part

def show(cq_obj, name="CQ_Object"):
    """Convert CadQuery Workplane to FreeCAD Part::Feature."""
    if not hasattr(cq_obj, "val"):
        FreeCAD.Console.PrintError("Input is not a cq.Workplane!\n")
        return
        
    import cadquery as cq
    try:
        # 使用原生 OCC 形状转换，避免临时文件读写
        occ_shape = cq_obj.val().wrapped
        shape = Part.Shape(occ_shape)
        
        # 【关键修复】处理 FreeCAD 文档的“薛定谔状态”
        doc = FreeCAD.ActiveDocument
        if not doc:
            docs = FreeCAD.listDocuments()
            if docs:
                doc = list(docs.values())[0]
            else:
                doc = FreeCAD.newDocument()
                
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        doc.recompute()
        
        FreeCAD.Console.PrintMessage(f"✅ Created FreeCAD object: {name}\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"❌ Creation failed: {str(e)}\n")
