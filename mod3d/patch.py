import numpy as np
import FreeCAD
import Part
from .utils import _is_vec, _vec, _tessellate, _tri_mesh_to_shape
from .deformers import brep_twist_z

# 因为 FreeCAD 的 Part.Shape 比较底层，我们需要保存原始方法
_orig_Shape_copy = Part.Shape.copy

def _shape_add(self, other):
    if _is_vec(other, 3):
        res = self.copy()
        res.translate(FreeCAD.Vector(*other))
        return res
    if isinstance(other, Part.Shape):
        return self.fuse(other).removeSplitter()
    raise ValueError(f"Unsupported operand for +: {type(other)}")

def _shape_sub(self, other):
    if isinstance(other, Part.Shape):
        return self.cut(other).removeSplitter()
    if _is_vec(other, 3):
        res = self.copy()
        res.translate(FreeCAD.Vector(-other[0], -other[1], -other[2]))
        return res
    raise ValueError(f"Unsupported operand for -: {type(other)}")

def _shape_mul(self, other):
    if isinstance(other, Part.Shape):
        return self.common(other).removeSplitter()
    if isinstance(other, (int, float)):
        res = self.copy()
        mat = FreeCAD.Matrix()
        mat.scale(other, other, other)
        return res.transformGeometry(mat)
    if _is_vec(other, 3):
        res = self.copy()
        mat = FreeCAD.Matrix()
        mat.scale(other[0], other[1], other[2])
        return res.transformGeometry(mat)
    raise ValueError(f"Unsupported operand for *: {type(other)}")

def _shape_matmul(self, angles):
    if not _is_vec(angles, 3):
        raise ValueError("Rotation expects [rx, ry, rz]")
    ax, ay, az = _vec(angles)
    res = self.copy()
    res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), np.degrees(ax))
    res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,1,0), np.degrees(ay))
    res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), np.degrees(az))
    return res

def _shape_mod(self, factors):
    if not _is_vec(factors, 6):
        raise ValueError("Shear expects [sxy, sxz, syx, syz, szx, szy]")
    sxy, sxz, syx, syz, szx, szy = _vec(factors)
    
    mat = FreeCAD.Matrix()
    mat.A12 = sxy
    mat.A13 = sxz
    mat.A21 = syx
    mat.A23 = syz
    mat.A31 = szx
    mat.A32 = szy
    
    res = self.copy()
    return res.transformGeometry(mat)

def _shape_xor(self, angles):
    if not _is_vec(angles, 3):
        raise ValueError("Twist expects [ax, ay, az]")
    ax, ay, az = _vec(angles)
    
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        try:
            res = brep_twist_z(self, az)
            if res is not None:
                return res
        except Exception:
            pass

    verts, faces = _tessellate(self, tol=0.1)
    new_verts = np.empty_like(verts)
    for i, (x, y, z) in enumerate(verts):
        tx, ty, tz = ax * x, ay * y, az * z
        Rx = np.array([[1, 0, 0], [0, np.cos(tx), -np.sin(tx)], [0, np.sin(tx),  np.cos(tx)]])
        Ry = np.array([[np.cos(ty), 0, np.sin(ty)], [0, 1, 0], [-np.sin(ty), 0, np.cos(ty)]])
        Rz = np.array([[np.cos(tz), -np.sin(tz), 0], [np.sin(tz),  np.cos(tz), 0], [0, 0, 1]])
        new_verts[i] = (Rx @ Ry @ Rz) @ np.array([x, y, z])
    return _tri_mesh_to_shape(new_verts, faces)

def _patch_shape():
    if getattr(Part.Shape, '_mod3d_patched', False):
        return
    Part.Shape.__add__    = _shape_add
    Part.Shape.__sub__    = _shape_sub
    Part.Shape.__mul__    = _shape_mul
    Part.Shape.__matmul__ = _shape_matmul
    Part.Shape.__mod__    = _shape_mod
    Part.Shape.__xor__    = _shape_xor
    Part.Shape._mod3d_patched = True

_patch_shape()