import numpy as np
import FreeCAD
import Part
from .utils import _is_vec, _vec, _tessellate, _tri_mesh_to_shape
from .deformers import brep_twist_z

class Shape:
    """一个轻量级的 Python 代理类，用来给不可变的 FreeCAD Part.Shape 穿上运算符的外衣"""
    def __init__(self, part_shape):
        self.shape = part_shape

    def __add__(self, other):
        if _is_vec(other, 3):
            res = self.shape.copy()
            res.translate(FreeCAD.Vector(*other))
            return Shape(res)
        if isinstance(other, Shape):
            return Shape(self.shape.fuse(other.shape).removeSplitter())
        if isinstance(other, Part.Shape):
            return Shape(self.shape.fuse(other).removeSplitter())
        raise ValueError(f"Unsupported operand for +: {type(other)}")

    def __sub__(self, other):
        if isinstance(other, Shape):
            return Shape(self.shape.cut(other.shape).removeSplitter())
        if isinstance(other, Part.Shape):
            return Shape(self.shape.cut(other).removeSplitter())
        if _is_vec(other, 3):
            res = self.shape.copy()
            res.translate(FreeCAD.Vector(-other[0], -other[1], -other[2]))
            return Shape(res)
        raise ValueError(f"Unsupported operand for -: {type(other)}")

    def __mul__(self, other):
        if isinstance(other, Shape):
            return Shape(self.shape.common(other.shape).removeSplitter())
        if isinstance(other, Part.Shape):
            return Shape(self.shape.common(other).removeSplitter())
        if isinstance(other, (int, float)):
            res = self.shape.copy()
            mat = FreeCAD.Matrix()
            mat.scale(other, other, other)
            return Shape(res.transformGeometry(mat))
        if _is_vec(other, 3):
            res = self.shape.copy()
            mat = FreeCAD.Matrix()
            mat.scale(other[0], other[1], other[2])
            return Shape(res.transformGeometry(mat))
        raise ValueError(f"Unsupported operand for *: {type(other)}")

    def __matmul__(self, angles):
        if not _is_vec(angles, 3):
            raise ValueError("Rotation expects [rx, ry, rz]")
        ax, ay, az = _vec(angles)
        res = self.shape.copy()
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), np.degrees(ax))
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,1,0), np.degrees(ay))
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), np.degrees(az))
        return Shape(res)

    def __mod__(self, factors):
        if not _is_vec(factors, 6):
            raise ValueError("Shear expects [sxy, sxz, syx, syz, szx, szy]")
        sxy, sxz, syx, syz, szx, szy = _vec(factors)
        mat = FreeCAD.Matrix()
        mat.A12, mat.A13 = sxy, sxz
        mat.A21, mat.A23 = syx, syz
        mat.A31, mat.A32 = szx, szy
        res = self.shape.copy()
        return Shape(res.transformGeometry(mat))

    def __xor__(self, angles):
        if not _is_vec(angles, 3):
            raise ValueError("Twist expects [ax, ay, az]")
        ax, ay, az = _vec(angles)
        
        if abs(ax) < 1e-6 and abs(ay) < 1e-6:
            try:
                res = brep_twist_z(self.shape, az)
                if res is not None:
                    return Shape(res)
            except Exception:
                pass

        verts, faces = _tessellate(self.shape, tol=0.1)
        new_verts = np.empty_like(verts)
        for i, (x, y, z) in enumerate(verts):
            tx, ty, tz = ax * x, ay * y, az * z
            Rx = np.array([[1, 0, 0], [0, np.cos(tx), -np.sin(tx)], [0, np.sin(tx),  np.cos(tx)]])
            Ry = np.array([[np.cos(ty), 0, np.sin(ty)], [0, 1, 0], [-np.sin(ty), 0, np.cos(ty)]])
            Rz = np.array([[np.cos(tz), -np.sin(tz), 0], [np.sin(tz),  np.cos(tz), 0], [0, 0, 1]])
            new_verts[i] = (Rx @ Ry @ Rz) @ np.array([x, y, z])
        return Shape(_tri_mesh_to_shape(new_verts, faces))

    # 透传 FreeCAD 的原生属性（比如 Volume, BoundBox 等）
    def __getattr__(self, name):
        return getattr(self.shape, name)

    def __repr__(self):
        return repr(self.shape)
