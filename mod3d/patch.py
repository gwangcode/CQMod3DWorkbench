import numpy as np
import FreeCAD
import Part
from .utils import _is_vec, _vec, _tessellate, _tri_mesh_to_shape
from .deformers import brep_twist_z

class Shape:
    def __init__(self, part_shape, is_transform=False, op=None, left=None, right=None, doc_name=None):
        self.shape = part_shape
        self._is_transform = is_transform
        self.op = op          # 操作类型："fuse", "cut", "common"
        self.left = left      # 左子节点
        self.right = right    # 右子节点
        self.doc_name = doc_name # 如果是文档里已有的模型，记录它的名字

    def __add__(self, other):
        if _is_vec(other, 3):
            res = self.shape.copy()
            res.translate(FreeCAD.Vector(*other))
            return Shape(res, is_transform=True, doc_name=self.doc_name)
        if isinstance(other, Shape):
            fused = self.shape.fuse(other.shape).removeSplitter()
            return Shape(fused, op="fuse", left=self, right=other)
        if isinstance(other, Part.Shape):
            fused = self.shape.fuse(other).removeSplitter()
            return Shape(fused, op="fuse", left=self, right=Shape(other))
        raise ValueError(f"Unsupported operand for +: {type(other)}")

    def __sub__(self, other):
        if isinstance(other, Shape):
            cut = self.shape.cut(other.shape).removeSplitter()
            return Shape(cut, op="cut", left=self, right=other)
        if isinstance(other, Part.Shape):
            cut = self.shape.cut(other).removeSplitter()
            return Shape(cut, op="cut", left=self, right=Shape(other))
        if _is_vec(other, 3):
            res = self.shape.copy()
            res.translate(FreeCAD.Vector(-other[0], -other[1], -other[2]))
            return Shape(res, is_transform=True, doc_name=self.doc_name)
        raise ValueError(f"Unsupported operand for -: {type(other)}")

    def __mul__(self, other):
        if isinstance(other, Shape):
            common = self.shape.common(other.shape).removeSplitter()
            return Shape(common, op="common", left=self, right=other)
        if isinstance(other, Part.Shape):
            common = self.shape.common(other).removeSplitter()
            return Shape(common, op="common", left=self, right=Shape(other))
        if isinstance(other, (int, float)):
            res = self.shape.copy()
            mat = FreeCAD.Matrix()
            mat.scale(other, other, other)
            return Shape(res.transformGeometry(mat), is_transform=True)
        if _is_vec(other, 3):
            res = self.shape.copy()
            mat = FreeCAD.Matrix()
            mat.scale(other[0], other[1], other[2])
            return Shape(res.transformGeometry(mat), is_transform=True)
        raise ValueError(f"Unsupported operand for *: {type(other)}")

    def __matmul__(self, angles):
        if not _is_vec(angles, 3):
            raise ValueError("Rotation expects [rx, ry, rz]")
        ax, ay, az = _vec(angles)
        res = self.shape.copy()
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), np.degrees(ax))
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,1,0), np.degrees(ay))
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), np.degrees(az))
        return Shape(res, is_transform=True)

    def __mod__(self, factors):
        if not _is_vec(factors, 6):
            raise ValueError("Shear expects [sxy, sxz, syx, syz, szx, szy]")
        sxy, sxz, syx, syz, szx, szy = _vec(factors)
        mat = FreeCAD.Matrix()
        mat.A12, mat.A13 = sxy, sxz
        mat.A21, mat.A23 = syx, syz
        mat.A31, mat.A32 = szx, szy
        res = self.shape.copy()
        return Shape(res.transformGeometry(mat), is_transform=False)

    def __xor__(self, angles):
        if not _is_vec(angles, 3):
            raise ValueError("Twist expects [ax, ay, az]")
        ax, ay, az = _vec(angles)
        
        if abs(ax) < 1e-6 and abs(ay) < 1e-6:
            try:
                res = brep_twist_z(self.shape, az)
                if res is not None:
                    return Shape(res, is_transform=False)
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
        return Shape(_tri_mesh_to_shape(new_verts, faces), is_transform=False)

    def __getattr__(self, name):
        return getattr(self.shape, name)

    def __repr__(self):
        return repr(self.shape)
