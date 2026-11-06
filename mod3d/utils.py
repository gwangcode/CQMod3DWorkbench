import numpy as np
import FreeCAD
import Part
import Mesh

def _is_vec(x, n: int) -> bool:
    """Support FreeCAD.Vector / list / tuple / ndarray"""
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
    """Convert triangular meshes back to B-rep solids using the FreeCAD native API"""
    mesh = Mesh.Mesh()
    
    # Constructing a triangle by directly passing 9 floats offers the best compatibility.
    for f in faces:
        v0, v1, v2 = verts[f[0]], verts[f[1]], verts[f[2]]
        mesh.addFacet(
            float(v0[0]), float(v0[1]), float(v0[2]),
            float(v1[0]), float(v1[1]), float(v1[2]),
            float(v2[0]), float(v2[1]), float(v2[2])
        )
    
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.1)
    
    # Try converting to solids to ensure subsequent boolean operations run smoothly.
    try:
        solid = Part.makeSolid(shape)
        if hasattr(solid, 'ShapeType') and solid.ShapeType == "Solid":
            shape = solid
    except Exception:
        # If the conversion fails, maintain the original shape (potentially a shell).
        pass
        
    return shape

def extremes(part) -> tuple:
    bb = part.BoundBox
    return bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax
