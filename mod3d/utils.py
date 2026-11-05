import numpy as np
import FreeCAD
import Part
import Mesh
import MeshPart


def _is_vec(x, n: int) -> bool:
    """支持 FreeCAD.Vector / list / tuple / ndarray"""
    if isinstance(x, FreeCAD.Vector):
        return n == 3
    try:
        arr = np.asarray(x)
        return arr.ndim == 1 and arr.size == n and np.issubdtype(arr.dtype, np.number)
    except Exception:
        return False


def _vec(x) -> tuple:
    return tuple(float(v) for v in x)


def _tessellate(shape, tol: float = 0.1):
    """FreeCAD Shape -> (verts, faces)"""
    if isinstance(shape, FreeCAD.Vector) or isinstance(shape, (int, float)):
        return np.array([]), []
    verts, faces = shape.tessellate(tol)
    vert_array = np.array([[v.x, v.y, v.z] for v in verts])
    return vert_array, faces


def _tri_mesh_to_shape(verts, faces, name="CQ_Object"):
    """使用 FreeCAD 的 MeshPart 将三角网格转回 B-rep 实体"""
    mesh = Mesh.Mesh()
    for f in faces:
        mesh.addFacet(
            # 【核心修复】将 Mesh.Vector 替换为 FreeCAD.Vector
            Mesh.MeshPoint(FreeCAD.Vector(*verts[f[0]])),
            Mesh.MeshPoint(FreeCAD.Vector(*verts[f[1]])),
            Mesh.MeshPoint(FreeCAD.Vector(*verts[f[2]]))
        )
    shape = MeshPart.meshToShape(mesh, 0.1)
    # 若是 Shell 则尝试转为 Solid
    if hasattr(shape, 'ShapeType') and shape.ShapeType != "Solid":
        try:
            shape = Part.makeSolid(shape)
        except Exception:
            pass
    return shape


def extremes(part) -> tuple:
    bb = part.BoundBox
    return bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax
