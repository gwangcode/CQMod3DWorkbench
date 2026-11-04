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
        # 通过 BREP 文件进行最稳妥的格式转换
        cq.exporters.export(cq_obj, temp_brep_path, "BREP")
        
        shape = Part.Shape()
        shape.read(temp_brep_path)
        
        # 确保有活动文档
        if not FreeCAD.ActiveDocument:
            FreeCAD.newDocument()
            
        # 核心修复：不使用 Part.show()，而是直接向文档添加对象
        # 这样可以彻底避免在无 GUI 环境（如 CI）中的视图刷新崩溃
        obj = FreeCAD.ActiveDocument.addObject("Part::Feature", name)
        obj.Shape = shape
        FreeCAD.ActiveDocument.recompute()
        
        FreeCAD.Console.PrintMessage(f"✅ 已生成 FreeCAD 对象: {name}\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"❌ 生成失败: {str(e)}\n")
    finally:
        # 清理临时文件
        if os.path.exists(temp_brep_path):
            os.unlink(temp_brep_path)
