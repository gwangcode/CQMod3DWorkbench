# ==========================================
# 测试 6：平滑实体生成 (smooth_body)
# ==========================================
def test_smooth_body_coplanar(term):
    """测试共面点集生成 2D 曲面"""
    # 这些点全在 Z=0 平面上
    pts = [(0,0,0), (10,0,0), (15,10,0), (10,20,0), (0,20,0), (-5,10,0)]
    
    term.execute_code(f"smooth_body({pts})")
    
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "未成功生成对象"
    assert obj.Shape.ShapeType == "Face", "共面点应生成平面(Face)"
    assert obj.Shape.isValid(), "生成的面无效"

def test_smooth_body_non_coplanar(term):
    """测试非共面点集生成 3D 平滑实体"""
    # 这些点在空间中有高低起伏
    pts = [(0,0,0), (10,0,5), (15,10,-2), (10,20,8), (0,20,0), (-5,10,5)]
    
    term.execute_code(f"smooth_body({pts})")
    
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "未成功生成对象"
    
    # 即使底层是凸包平滑，ShapeType 最终应当被封装为 Solid
    assert obj.Shape.ShapeType in ("Solid", "CompSolid"), "非共面点应生成三维实体"
    assert obj.Shape.Volume > 0, "生成的实体体积必须大于 0"
    assert obj.Shape.isValid(), "生成的平滑实体无效"

def test_smooth_body_insufficient_points(term):
    """测试点数不足时的异常处理"""
    term.write = MagicMock()
    # 只有 3 个点，无法构造成体
    term.execute_code("smooth_body([(0,0,0), (10,0,0), (0,10,0)])")
    
    # 终端应该捕获到了 ValueError
    term.write.assert_called_once()
    assert "At least 4 points are required" in term.write.call_args[0][0]
