import Part
import FreeCAD

def show(cq_obj, name="CQ_Object"):
    """将 CadQuery Workplane 对象转换为 FreeCAD 实体并显示在视图中。"""
    if not hasattr(cq_obj, "val"):
        FreeCAD.Console.PrintError("传入的对象不是 cq.Workplane！\n")
        return
        
    try:
        # 直接获取底层的 OCC 拓扑结构 (TopoDS_Shape)
        # 彻底抛弃临时 BREP 文件，避免任何文件读写权限或无头环境报错
        occ_shape = cq_obj.val().wrapped
        shape = Part.Shape(occ_shape)
        
        # 确保有活动文档
        if not FreeCAD.ActiveDocument:
            FreeCAD.newDocument()
            
        Part.show(shape, name)
        FreeCAD.Console.PrintMessage(f"✅ 已生成 FreeCAD 对象: {name}\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"❌ 生成失败: {str(e)}\n")
