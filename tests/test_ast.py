import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock PySide 组件，防止实例化 UI
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()

import FreeCAD
import Part
import mod3d

# 提取终端中的核心逻辑
from terminal import PythonTerminal

@pytest.fixture
def clean_doc():
    """每次测试前提供一个干净的文档"""
    doc = FreeCAD.newDocument("TestDoc")
    FreeCAD.setActiveDocument("TestDoc")
    yield doc
    FreeCAD.closeDocument("TestDoc")

def test_build_tree_fusion(clean_doc):
    """测试 A + B 生成 Fusion 节点"""
    term = PythonTerminal()
    
    # 伪造两个已有的 Part 节点
    obj1 = clean_doc.addObject("Part::Box", "model_1")
    obj1.Shape = Part.makeBox(10, 10, 10)
    obj2 = clean_doc.addObject("Part::Sphere", "model_2")
    obj2.Shape = Part.makeSphere(5)
    
    # 在终端里伪造一个加法节点
    shape1 = mod3d.Shape(obj1.Shape, doc_name="model_1")
    shape2 = mod3d.Shape(obj2.Shape, doc_name="model_2")
    ast_result = shape1 + shape2
    
    # 执行建树
    root_obj = term._build_tree(ast_result, clean_doc)
    
    assert root_obj.TypeId == "Part::MultiFuse"
    assert "model_1" in [o.Name for o in root_obj.Shapes]
    assert "model_2" in [o.Name for o in root_obj.Shapes]

def test_build_tree_cut_and_noise(clean_doc):
    """测试 (A - B) 后套用 Noise 的复杂层级"""
    term = PythonTerminal()
    
    obj1 = clean_doc.addObject("Part::Box", "model_1")
    obj1.Shape = Part.makeBox(10, 10, 10)
    obj2 = clean_doc.addObject("Part::Sphere", "model_2")
    obj2.Shape = Part.makeSphere(8)
    
    shape1 = mod3d.Shape(obj1.Shape, doc_name="model_1")
    shape2 = mod3d.Shape(obj2.Shape, doc_name="model_2")
    
    # A - B 产生 Cut 树
    cut_ast = shape1 - shape2
    
    # 套一层噪声
    noise_ast = mod3d.apply_noise(cut_ast, seed=42)
    
    root_obj = term._build_tree(noise_ast, clean_doc)
    
    # 顶层应该是 Noise
    assert root_obj.TypeId == "Part::FeaturePython"
    assert root_obj.Name.startswith("Noise")
    
    # Noise 的下级应该是 Cut
    base_obj = root_obj.Base
    assert base_obj.TypeId == "Part::Cut"
    assert base_obj.Base.Name == "model_1"
    assert base_obj.Tool.Name == "model_2"
