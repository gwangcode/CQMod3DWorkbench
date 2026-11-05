import pytest
import FreeCAD
import Part
import sys
import os

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 确保 mod3d 被导入并打上补丁
import mod3d
from mod3d.patch import _patch_shape

def test_mod3d_primitives():
    """测试原生的图元生成"""
    box = mod3d.cube(10)
    assert isinstance(box, Part.Shape)
    assert abs(box.Volume - 1000.0) < 1e-3
    
    sph = mod3d.sphere(5)
    assert isinstance(sph, Part.Shape)
    # 体积约 523.6
    assert abs(sph.Volume - (4/3 * 3.14159 * 125)) < 1.0

def test_mod3d_operator_patch():
    """测试打上补丁后的运算符重载"""
    box = mod3d.cube(10)
    
    # 测试平移 (+ [x, y, z])
    moved = box + [10, 0, 0]
    assert moved.BoundBox.XMin == 5.0
    assert moved.BoundBox.XMax == 15.0
    
    # 测试布尔差集 (shape - shape)
    sphere = mod3d.sphere(6)
    cut_shape = box - sphere
    assert cut_shape.Volume < box.Volume
    
    # 测试旋转 (@ [rx, ry, rz])
    rotated = box @ [0, 0, 1.5708] # 旋转 90 度
    assert isinstance(rotated, Part.Shape)
