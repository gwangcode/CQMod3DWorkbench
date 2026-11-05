import numpy as np
import FreeCAD
import Part
import Mesh
import MeshPart

def _is_vec(x, n: int) -> bool:
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
    # FreeCAD tessellate 返回的是 (vertices, facets)
    verts, faces = shape.tessellate(tol)
    vert_array = np.array([[v.x, v.y, v.z] for v in verts])
    return vert_array, faces

def _tri_mesh_to_shape(verts, faces, name="CQ_Object"):
    """使用 FreeCAD 的 MeshPart 极速将三角网格转回 B-rep 实体"""
    mesh = Mesh.Mesh()
    for f in faces:
        mesh.addFacet(
            Mesh.MeshPoint(Mesh.Vector(*verts[f[0]])),
            Mesh.MeshPoint(Mesh.Vector(*verts[f[1]])),
            Mesh.MeshPoint(Mesh.Vector(*verts[f[2]]))
        )
    # 转回 B-rep 实体
    shape = MeshPart.meshToShape(mesh, 0.1)
    return shape

def extremes(part) -> tuple:
    """返回包围盒"""
    bb = part.BoundBox
    return bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax