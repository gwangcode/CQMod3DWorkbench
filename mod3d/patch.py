import numpy as np
import FreeCAD
import Part
from .utils import _is_vec, _vec, _tessellate, _tri_mesh_to_shape
from .deformers import brep_twist_z

class Shape:
    def __init__(self, part_shape, is_transform=False, op=None, children=None, doc_name=None, transform_data=None):
        self.shape = part_shape
        self._is_transform = is_transform
        self.op = op                  # "fuse", "cut", "common", "transform"
        self.children = children or [] # 子节点列表 (平铺，避免 A+B+C 变成多层嵌套)
        self.doc_name = doc_name      # 如果在文档里已存在
        self.transform_data = transform_data # 记录平移/旋转/缩放的具体数值

    def __add__(self, other):
        if _is_vec(other, 3):
            res = self.shape.copy()
            res.translate(FreeCAD.Vector(*other))
            # 记录成 Transform 节点，包裹原先的节点
            return Shape(res, op="transform", children=[self], transform_data=("translate", other))
        if isinstance(other, Shape):
            # 如果左边已经是 fuse，直接把右边加进 children，生成 MultiFuse
            if self.op == "fuse": return Shape(self.shape.fuse(other.shape).removeSplitter(), op="fuse", children=self.children + [other])
            return Shape(self.shape.fuse(other.shape).removeSplitter(), op="fuse", children=[self, other])
        if isinstance(other, Part.Shape):
            if self.op == "fuse": return Shape(self.shape.fuse(other).removeSplitter(), op="fuse", children=self.children + [Shape(other)])
            return Shape(self.shape.fuse(other).removeSplitter(), op="fuse", children=[self, Shape(other)])
        raise ValueError(f"Unsupported operand for +: {type(other)}")

    def __sub__(self, other):
        if isinstance(other, Shape):
            return Shape(self.shape.cut(other.shape).removeSplitter(), op="cut", children=[self, other])
        if isinstance(other, Part.Shape):
            return Shape(self.shape.cut(other).removeSplitter(), op="cut", children=[self, Shape(other)])
        if _is_vec(other, 3):
            res = self.shape.copy()
            res.translate(FreeCAD.Vector(-other[0], -other[1], -other[2]))
            return Shape(res, op="transform", children=[self], transform_data=("translate", (-other[0], -other[1], -other[2])))
        raise ValueError(f"Unsupported operand for -: {type(other)}")

    def __mul__(self, other):
        if isinstance(other, Shape):
            if self.op == "common": return Shape(self.shape.common(other.shape).removeSplitter(), op="common", children=self.children + [other])
            return Shape(self.shape.common(other.shape).removeSplitter(), op="common", children=[self, other])
        if isinstance(other, Part.Shape):
            if self.op == "common": return Shape(self.shape.common(other).removeSplitter(), op="common", children=self.children + [Shape(other)])
            return Shape(self.shape.common(other).removeSplitter(), op="common", children=[self, Shape(other)])
        if isinstance(other, (int, float)):
            res = self.shape.copy()
            mat = FreeCAD.Matrix()
            mat.scale(other, other, other)
            return Shape(res.transformGeometry(mat), op="transform", children=[self], transform_data=("scale", (other, other, other)))
        if _is_vec(other, 3):
            res = self.shape.copy()
            mat = FreeCAD.Matrix()
            mat.scale(other[0], other[1], other[2])
            return Shape(res.transformGeometry(mat), op="transform", children=[self], transform_data=("scale", other))
        raise ValueError(f"Unsupported operand for *: {type(other)}")

    def __matmul__(self, angles):
        if not _is_vec(angles, 3):
            raise ValueError("Rotation expects [rx, ry, rz]")
        ax, ay, az = _vec(angles)
        res = self.shape.copy()
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(1,0,0), np.degrees(ax))
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,1,0), np.degrees(ay))
        res.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), np.degrees(az))
        return Shape(res, op="transform", children=[self], transform_data=("rotate", angles))

    def __mod__(self, factors):
        if not _is_vec(factors, 6): raise ValueError("Shear expects 6 factors")
        sxy, sxz, syx, syz, szx, szy = _vec(factors)
        mat = FreeCAD.Matrix()
        mat.A12, mat.A13 = sxy, sxz
        mat.A21, mat.A23 = syx, syz
        mat.A31, mat.A32 = szx, szy
        res = self.shape.copy()
        return Shape(res.transformGeometry(mat), op="transform", children=[self], transform_data=("shear", factors))

    def __xor__(self, angles):
        if not _is_vec(angles, 3): raise ValueError("Twist expects 3 angles")
        ax, ay, az = _vec(angles)
        
        if abs(ax) < 1e-6 and abs(ay) < 1e-6:
            try:
                res = brep_twist_z(self.shape, az)
                if res is not None:
                    return Shape(res, op="twist", children=[self])
            except Exception: pass

        verts, faces = _tessellate(self.shape, tol=0.1)
        new_verts = np.empty_like(verts)
        for i, (x, y, z) in enumerate(verts):
            tx, ty, tz = ax * x, ay * y, az * z
            Rx = np.array([[1, 0, 0], [0, np.cos(tx), -np.sin(tx)], [0, np.sin(tx),  np.cos(tx)]])
            Ry = np.array([[np.cos(ty), 0, np.sin(ty)], [0, 1, 0], [-np.sin(ty), 0, np.cos(ty)]])
            Rz = np.array([[np.cos(tz), -np.sin(tz), 0], [np.sin(tz),  np.cos(tz), 0], [0, 0, 1]])
            new_verts[i] = (Rx @ Ry @ Rz) @ np.array([x, y, z])
        return Shape(_tri_mesh_to_shape(new_verts, faces), op="twist", children=[self])

    def __getattr__(self, name):
        return getattr(self.shape, name)

    def __repr__(self):
        return repr(self.shape)
