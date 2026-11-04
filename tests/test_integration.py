import sys
import os

# --- 动态探测 FreeCAD 的路径并加入 sys.path ---
if 'CONDA_PREFIX' in os.environ:
    prefix = os.environ['CONDA_PREFIX']
    # 寻找 FreeCAD.so 或 FreeCAD.py
    freecad_lib = os.path.join(prefix, 'lib', 'freecad', 'lib')
    if os.path.exists(freecad_lib) and freecad_lib not in sys.path:
        sys.path.append(freecad_lib)
    # 寻找 site-packages
    site_packages = os.path.join(prefix, 'lib', 'python3.11', 'site-packages')
    if os.path.exists(site_packages) and site_packages not in sys.path:
        sys.path.append(site_packages)

import FreeCAD
import Part
import cadquery as cq

# 导入你的真实工具
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils

def test_real_geometry_conversion():
    """真实测试：CadQuery 导出 BREP -> FreeCAD 读取 -> 验证体积"""
    # 1. 创建一个真实的 CadQuery 立方体
    box = cq.Workplane("XY").box(10, 10, 10)
    
    # 2. 创建一个新的 FreeCAD 文档
    doc = FreeCAD.newDocument("TestDoc")
    
    # 3. 调用你的转换函数
    utils.show(box, name="RealBox")
    
    # 4. 验证 FreeCAD 文档里是否真的生成了对象
    obj = doc.getObject("RealBox")
    assert obj is not None, "FreeCAD 中没有找到生成的对象"
    
    # 5. 验证几何属性（体积应该是 10*10*10 = 1000）
    vol = obj.Shape.Volume
    assert abs(vol - 1000.0) < 1e-3, f"生成的几何体体积错误: {vol}"
    
    # 清理文档
    FreeCAD.closeDocument("TestDoc")
