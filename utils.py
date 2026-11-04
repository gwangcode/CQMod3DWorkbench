import os
import tempfile
import FreeCAD
import Part

def show(cq_obj, name="CQ_Object"):
    """将 CadQuery Workplane 对象转换为 FreeCAD 实体并显示在视图中。"""
    if not hasattr(cq_obj, "val"):
        FreeCAD.Console.PrintError("传入的对象不是 cq.Workplane！\n")
        return
        
    temp_brep = tempfile.NamedTemporaryFile(suffix=".brep", delete=False)
    temp_brep_path = temp_brep.name
    temp_brep.close()
    
    try:
        import cadquery as cq
        cq.exporters.export(cq_obj, temp_brep_path, "BREP")
        
        shape = Part.Shape()
        shape.read(temp_brep_path)
        
        doc = FreeCAD.ActiveDocument
        if not doc:
            # 无头环境核心修复：如果活动文档为空，尝试获取列表中已存在的文档
            docs = FreeCAD.listDocuments()
            if docs:
                doc = list(docs.values())[0]
            else:
                doc = FreeCAD.newDocument()
                
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        doc.recompute()
        
        FreeCAD.Console.PrintMessage(f"✅ 已生成 FreeCAD 对象: {name}\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"❌ 生成失败: {str(e)}\n")
    finally:
        if os.path.exists(temp_brep_path):
            os.unlink(temp_brep_path)
