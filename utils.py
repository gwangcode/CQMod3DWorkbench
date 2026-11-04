import os
import tempfile
import FreeCAD
import Part

def show(cq_obj, name="CQ_Object"):
    """将 CadQuery Workplane 对象转换为 FreeCAD 实体并显示在视图中。"""
    if not hasattr(cq_obj, "val"):
        FreeCAD.Console.PrintError("Input is not a cq.Workplane!\n")
        return None
        
    temp_brep = tempfile.NamedTemporaryFile(suffix=".brep", delete=False)
    temp_brep_path = temp_brep.name
    temp_brep.close()
    
    try:
        import cadquery as cq
        # 通过 BREP 文件中转，避免底层内存直接转换导致的段错误
        cq.exporters.export(cq_obj, temp_brep_path, "BREP")
        
        shape = Part.Shape()
        shape.read(temp_brep_path)
        
        doc = FreeCAD.ActiveDocument
        if not doc:
            docs = FreeCAD.listDocuments()
            doc = list(docs.values())[0] if docs else FreeCAD.newDocument()
                
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        doc.recompute()
        
        FreeCAD.Console.PrintMessage(f"✅ Created FreeCAD object: {name}\n")
        # 【核心修改】把生成的对象返回，让终端能够获取它的属性
        return obj  
    except Exception as e:
        FreeCAD.Console.PrintError(f"❌ Creation failed: {str(e)}\n")
        return None
    finally:
        if os.path.exists(temp_brep_path):
            os.unlink(temp_brep_path)
