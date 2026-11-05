import pytest
import FreeCAD
import Part
import mod3d

# 注意：这里不需要再写 add_freecad_to_path，因为 conftest.py 已经全局接管了

@pytest.fixture
def clean_doc():
    """提供一个干净的测试文档，测试结束后销毁"""
    doc = FreeCAD.newDocument("ParamTest")
    FreeCAD.setActiveDocument("ParamTest")
    yield doc
    FreeCAD.closeDocument("ParamTest")

def test_parametric_noise_recompute(clean_doc):
    """测试单层依赖：修改 Base 的半径，Noise 节点自动更新"""
    from terminal import NoiseFeature

    base_obj = clean_doc.addObject("Part::Sphere", "BaseSphere")
    base_obj.Radius = 10
    
    noise_obj = clean_doc.addObject("Part::FeaturePython", "MyNoise")
    NoiseFeature(noise_obj)
    noise_obj.Base = base_obj
    noise_obj.Seed = 42
    noise_obj.Density = 0.5
    noise_obj.Amplitude = 1.0
    
    clean_doc.recompute()
    vol1 = noise_obj.Shape.Volume
    assert vol1 > 0
    
    # 修改底层 Sphere 半径，触发重算
    base_obj.Radius = 20
    clean_doc.recompute()
    vol2 = noise_obj.Shape.Volume
    assert vol2 > vol1  # 半径变大，噪声体积应变大


def test_cascade_parametric_update(clean_doc):
    """
    测试复杂多级级联树更新：
    构建 (Box - Sphere) -> Twist 的树
    1. 修改 Box 的尺寸
    2. 修改 Sphere 的半径
    验证最顶层的 Twist 节点是否每次都自动更新。
    """
    from terminal import PythonTerminal
    
    term = PythonTerminal()
    
    # 1. 创建底层原生图元
    box = clean_doc.addObject("Part::Box", "BaseBox")
    box.Length = 10
    box.Width = 10
    box.Height = 10
    
    sphere = clean_doc.addObject("Part::Sphere", "HoleSphere")
    sphere.Radius = 8
    
    # 2. 构建 AST：先做差集 (Box - Sphere)，然后再做扭转
    shape_box = mod3d.Shape(box.Shape, doc_name="BaseBox")
    shape_sphere = mod3d.Shape(sphere.Shape, doc_name="HoleSphere")
    
    ast_cut = shape_box - shape_sphere
    ast_twist = ast_cut ^ [0, 0, 0.1]
    
    # 3. 通过终端的神奇方法，将 AST 落地为真实的 FreeCAD 参数化特征树
    root_node = term._build_tree(ast_twist, clean_doc)
    clean_doc.recompute()
    
    # 验证树的拓扑结构
    assert root_node.TypeId == "Part::FeaturePython"  # Twist 节点
    assert root_node.Base.TypeId == "Part::Cut"       # 中间的 Cut 节点
    assert root_node.Base.Base.Name == "BaseBox"      # Cut 的底
    assert root_node.Base.Tool.Name == "HoleSphere"   # Cut 的工具
    
    # 记录初始体积
    vol_initial = root_node.Shape.Volume
    assert vol_initial > 0
    
    # =====================================================
    # 【核心测试 1】：修改最底层的 Box 尺寸（10 -> 20）
    # =====================================================
    box.Length = 20
    clean_doc.recompute()
    
    vol_after_box_change = root_node.Shape.Volume
    # 因为 Box 变长了，挖掉的球体相对变小，所以顶层的剩余体积必须变大
    assert vol_after_box_change > vol_initial, "修改底层 Box 后，顶层 Twist 未正确更新！"
    
    # =====================================================
    # 【核心测试 2】：修改中间的 Sphere 半径（8 -> 2）
    # =====================================================
    sphere.Radius = 2
    clean_doc.recompute()
    
    vol_after_sphere_change = root_node.Shape.Volume
    # 因为挖掉的球变小了，剩下的体积必须进一步变大
    assert vol_after_sphere_change > vol_after_box_change, "修改中间 Sphere 后，顶层 Twist 未正确更新！"
    
    # =====================================================
    # 【核心测试 3】：修改 Twist 节点的参数
    # =====================================================
    root_node.AngleZ = 0.5  # 增加扭转角度
    clean_doc.recompute()
    
    vol_after_twist_change = root_node.Shape.Volume
    # 改变扭转角度可能会导致体积发生微小变化（取决于几何体形状，此处只验证它发生了更新）
    assert vol_after_twist_change != vol_after_sphere_change, "修改 Twist 参数后，未重新计算！"

def test_extreme_multibranch_cascade(clean_doc):
    """
    地狱级测试：多分支、多层级、跨属性级联更新
    结构：
    Branch A: Fusion( Box , Sphere )
    Tool:     Cylinder
    Top:      Cut( Branch A , Tool )
    """
    from terminal import PythonTerminal
    term = PythonTerminal()

    # 1. 构建底层基础图元
    box = clean_doc.addObject("Part::Box", "BaseBox")
    box.Length, box.Width, box.Height = 10, 10, 10

    sphere = clean_doc.addObject("Part::Sphere", "BaseSphere")
    sphere.Radius = 5
    # 注意：我们把球体平移到了边缘
    sphere.Placement.Base = FreeCAD.Vector(10, 0, 0) 

    cyl = clean_doc.addObject("Part::Cylinder", "CutCylinder")
    cyl.Radius = 3
    cyl.Height = 20

    # 2. 用 AST 构建复杂的树逻辑： (Box + Sphere) - Cylinder
    s_box = mod3d.Shape(box.Shape, doc_name="BaseBox")
    s_sphere = mod3d.Shape(sphere.Shape, doc_name="BaseSphere")
    s_cyl = mod3d.Shape(cyl.Shape, doc_name="CutCylinder")

    fusion_ast = s_box + s_sphere
    final_ast = fusion_ast - s_cyl

    # 3. 落地为 FreeCAD 原生节点树
    root_node = term._build_tree(final_ast, clean_doc)
    clean_doc.recompute()

    # 验证拓扑结构
    assert root_node.TypeId == "Part::Cut"
    assert root_node.Base.TypeId == "Part::MultiFuse"
    
    vol_initial = root_node.Shape.Volume

    # =====================================================
    # 测试点 1：修改深层分支（Box 的尺寸）
    # =====================================================
    box.Length = 30
    clean_doc.recompute()
    vol_1 = root_node.Shape.Volume
    assert vol_1 > vol_initial, "修改深层 Box 长度失败！"

    # =====================================================
    # 测试点 2：修改深层分支（Sphere 的位置属性 Placement）
    # =====================================================
    # 之前球在 (10,0,0)，完全贴在盒子边缘。
    # 我们现在把它移到 (5,0,0)，让球体深深嵌进盒子里
    sphere.Placement.Base = FreeCAD.Vector(5, 0, 0)
    clean_doc.recompute()
    vol_2 = root_node.Shape.Volume
    # 球体深入盒子，意味着两者的融合体变小了，挖去圆柱后剩下的体积会变小
    assert vol_2 < vol_1, "修改深层 Sphere 的 Placement 失败！"

    # =====================================================
    # 测试点 3：修改中间层刀具（Cylinder 的半径）
    # =====================================================
    cyl.Radius = 8
    clean_doc.recompute()
    vol_3 = root_node.Shape.Volume
    # 刀具变粗了，挖掉的肉更多，最终体积必须变小
    assert vol_3 < vol_2, "修改中间层 Cylinder 半径失败！"

def test_destructive_transform_in_place(clean_doc):
    """
    【核心语义测试】验证破坏性变换（平移/旋转/缩放）是【原地修改 Placement】，
    而不是删除重建。
    - 操作后：原对象依然存在（身份不变、名称不变）
    - 操作后：没有生成多余的新节点
    - 操作后：Placement 被正确更新
    """
    from terminal import PythonTerminal
    term = PythonTerminal()

    # 1. 创建一个基础模型
    box = clean_doc.addObject("Part::Box", "MyBox")
    box.Length = 10
    box.Width = 10
    box.Height = 10
    box.Placement.Base = FreeCAD.Vector(0, 0, 0)

    # 记录初始状态：文档中的对象总数
    obj_count_before = len(clean_doc.Objects)
    assert obj_count_before == 1

    # 2. 在终端里执行平移操作（模拟用户敲入 part("MyBox") + [50, 0, 0]）
    term._consumed_targets = ["MyBox"]
    s_box = mod3d.Shape(box.Shape, doc_name="MyBox")
    ast_translated = s_box + [50, 0, 0]
    root = term._build_tree(ast_translated, clean_doc)
    clean_doc.recompute()

    # =====================================================
    # 【断言 1】：原对象必须依然存在，不能消失！
    # =====================================================
    assert clean_doc.getObject("MyBox") is not None, "破坏性变换错误地删除了原对象！"

    # =====================================================
    # 【断言 2】：文档中的对象总数不变，没有生成新节点！
    # =====================================================
    assert len(clean_doc.Objects) == obj_count_before, \
        "破坏性变换错误地创建了新节点，应该原地修改！"

    # =====================================================
    # 【断言 3】：root_obj 就是原对象本身（身份未变）
    # =====================================================
    assert root.Name == "MyBox", "返回的对象不是原对象，身份丢失！"

    # =====================================================
    # 【断言 4】：Placement 被正确更新（X 方向移动了 50）
    # =====================================================
    assert abs(box.Placement.Base.x - 50.0) < 1e-5, "Placement 未被正确更新！"


def test_destructive_rotation_in_place(clean_doc):
    """验证旋转操作同样是原地修改 Placement"""
    from terminal import PythonTerminal
    term = PythonTerminal()

    box = clean_doc.addObject("Part::Box", "RotBox")
    box.Length, box.Width, box.Height = 10, 20, 5
    
    obj_count_before = len(clean_doc.Objects)
    
    # 绕 Z 轴旋转 90 度
    s_box = mod3d.Shape(box.Shape, doc_name="RotBox")
    ast = s_box @ [0, 0, 1.5708]
    term._build_tree(ast, clean_doc)
    clean_doc.recompute()

    # 断言原对象未被删除
    assert clean_doc.getObject("RotBox") is not None
    # 断言没有新对象被创建
    assert len(clean_doc.Objects) == obj_count_before
    # 断言旋转角度被应用（Placement.Rotation 不为单位四元数）
    assert box.Placement.Rotation.Angle > 1.0


def test_destructive_scale_creates_new_node(clean_doc):
    """
    注意：缩放与平移/旋转不同！
    因为 FreeCAD 没有原生的'缩放置换'属性，缩放必须烘焙到几何里，
    所以它会生成一个新节点（保留原对象）。
    """
    from terminal import PythonTerminal
    term = PythonTerminal()

    box = clean_doc.addObject("Part::Box", "ScaleBox")
    box.Length = 10
    
    s_box = mod3d.Shape(box.Shape, doc_name="ScaleBox")
    ast = s_box * 2.0  # 均匀放大 2 倍
    root = term._build_tree(ast, clean_doc)
    clean_doc.recompute()

    # 缩放必须生成新节点（因为 Shape 变了，不是 Placement 能表达的）
    assert root.Name != "ScaleBox", "缩放应该生成新对象，因为几何本身变了！"
    # 原对象依然保留（非破坏性）
    assert clean_doc.getObject("ScaleBox") is not None
    # 缩放后体积变为原来的 8 倍
    assert abs(root.Shape.Volume - 8000.0) < 1.0
