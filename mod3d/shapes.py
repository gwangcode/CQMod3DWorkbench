import numpy as np
import FreeCAD
import Part
from typing import Union, List
from .utils import _is_vec, _vec

class Shape2d:
    def __init__(self, vertices: Union[List[List[float]], np.ndarray]):
        self.vertices = np.asarray(vertices, dtype=float).reshape(-1, 2)

    def extremes(self) -> tuple:
        v = self.vertices
        return v[:,0].min(), v[:,0].max(), v[:,1].max(), v[:,1].min()

    def _shapely_op(self, other: 'Shape2d', op: str) -> 'Shape2d':
        from shapely.geometry import Polygon
        p1, p2 = Polygon(self.vertices), Polygon(other.vertices)
        if not p1.is_valid: p1 = p1.buffer(0)
        if not p2.is_valid: p2 = p2.buffer(0)
        res = getattr(p1, op)(p2)
        if res.is_empty: return Shape2d(np.zeros((0, 2)))
        if res.geom_type == 'MultiPolygon':
            res = max(res.geoms, key=lambda g: g.area)
        return Shape2d(np.asarray(res.exterior.coords))

    def __add__(self, o: Union['Shape2d', List[float]]) -> 'Shape2d':
        if isinstance(o, Shape2d): return self._shapely_op(o, 'union')
        if _is_vec(o, 2):          return Shape2d(self.vertices + np.asarray(o))
        raise ValueError(f"Unsupported operand for +: {type(o)}")

    def __sub__(self, o: Union['Shape2d', List[float]]) -> 'Shape2d':
        if isinstance(o, Shape2d): return self._shapely_op(o, 'difference')
        if _is_vec(o, 2):          return Shape2d(self.vertices - np.asarray(o))
        raise ValueError(f"Unsupported operand for -: {type(o)}")

    def __mul__(self, o: Union['Shape2d', float, List[float]]) -> 'Shape2d':
        if isinstance(o, Shape2d): return self._shapely_op(o, 'intersection')
        if isinstance(o, (int, float)): return Shape2d(self.vertices * o)
        if _is_vec(o, 2):          return Shape2d(self.vertices * np.asarray(o))
        raise ValueError(f"Unsupported operand for *: {type(o)}")

    def __matmul__(self, angle: float) -> 'Shape2d':
        c, s = np.cos(angle), np.sin(angle)
        R = np.array([[c, -s], [s, c]])
        cen = self.vertices.mean(axis=0)
        return Shape2d((self.vertices - cen) @ R.T + cen)

    def __mod__(self, factors: List[float]) -> 'Shape2d':
        a, b = _vec(factors)
        Sx = np.array([[1, np.tan(a)], [0, 1]])
        Sy = np.array([[1, 0], [np.tan(b), 1]])
        return Shape2d(self.vertices @ (Sx @ Sy).T)

    def __invert__(self) -> 'Shape2d':
        v = self.vertices
        if len(v) and np.allclose(v[0], v[-1]): return Shape2d(v[:-1])
        return Shape2d(np.vstack([v, v[0]]))

    def to_face(self) -> Part.Shape:
        """转为 FreeCAD 的平面"""
        vecs = [FreeCAD.Vector(p[0], p[1], 0) for p in self.vertices]
        if not np.allclose(self.vertices[0], self.vertices[-1]):
            vecs.append(vecs[0])
        wire = Part.makePolygon(vecs)
        return Part.Face(wire)

    def __repr__(self) -> str: return f"Shape2d(n={len(self.vertices)})"


class Shape3d:
    def __init__(self, shape: Union['Shape2d', np.ndarray, List], z: float = 0):
        if isinstance(shape, Shape2d):
            v = shape.vertices
            self.vertices = np.hstack([v, np.full((v.shape[0], 1), z)])
        else:
            arr = np.asarray(shape, dtype=float)
            if arr.ndim == 1: arr = arr.reshape(1, -1)
            if arr.shape[1] == 2:
                self.vertices = np.hstack([arr, np.full((arr.shape[0], 1), z)])
            else:
                self.vertices = arr

    def __add__(self, o: List[float]) -> 'Shape3d':
        if _is_vec(o, 3): return Shape3d(self.vertices + np.asarray(o))
        raise ValueError

    def __sub__(self, o: List[float]) -> 'Shape3d':
        if _is_vec(o, 3): return Shape3d(self.vertices - np.asarray(o))
        raise ValueError

    def __mul__(self, o: List[float]) -> 'Shape3d':
        if _is_vec(o, 3): return Shape3d(self.vertices * np.asarray(o))
        raise ValueError

    def __matmul__(self, angles: List[float]) -> 'Shape3d':
        ax, ay, az = _vec(angles)
        Rx = np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
        Ry = np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]])
        Rz = np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
        return Shape3d(self.vertices @ (Rz @ Ry @ Rx).T)

    def __mod__(self, factors: List[float]) -> 'Shape3d':
        sxy, sxz, syx, syz, szx, szy = _vec(factors)
        S = np.array([[1,sxy,sxz],[syx,1,syz],[szx,szy,1]])
        return Shape3d(self.vertices @ S.T)

    def __xor__(self, angles: List[float]) -> 'Shape3d':
        ax, ay, az = _vec(angles)
        new = np.empty_like(self.vertices)
        for i, (x, y, z) in enumerate(self.vertices):
            tx, ty, tz = ax*x, ay*y, az*z
            Rx = np.array([[1,0,0],[0,np.cos(tx),-np.sin(tx)],[0,np.sin(tx),np.cos(tx)]])
            Ry = np.array([[np.cos(ty),0,np.sin(ty)],[0,1,0],[-np.sin(ty),0,np.cos(ty)]])
            Rz = np.array([[np.cos(tz),-np.sin(tz),0],[np.sin(tz),np.cos(tz),0],[0,0,1]])
            new[i] = (Rx @ Ry @ Rz) @ np.array([x, y, z])
        return Shape3d(new)

    def __invert__(self) -> 'Shape3d':
        v = self.vertices
        if len(v) and np.allclose(v[0], v[-1]): return Shape3d(v[:-1])
        return Shape3d(np.vstack([v, v[0]]))

    def to_wire(self) -> Part.Shape:
        vecs = [FreeCAD.Vector(v[0], v[1], v[2]) for v in self.vertices]
        return Part.makePolygon(vecs)

    def __repr__(self) -> str: return f"Shape3d(n={len(self.vertices)})"


def solenoid(cross_section: Shape2d, dz: float = 0.1, n_coils: int = 10) -> Shape3d:
    return Shape3d(np.vstack([Shape3d(cross_section, i*dz).vertices for i in range(n_coils)]))