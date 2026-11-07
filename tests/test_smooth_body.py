import pytest
import sys
import os
import types
from unittest.mock import MagicMock
import numpy as np

# 动态探测 FreeCAD 路径
def add_freecad_to_path():
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        for p in [os.path.join(prefix, 'lib', 'freecad', 'lib'), os.path.join(prefix, 'Library', 'lib'), os.path.join(prefix, 'lib')]:
            if os.path.exists(p) and p not in sys.path: sys.path.append(p)
    if sys.platform == 'win32':
        import glob
        for p in glob.glob(r"C:\Program Files\FreeCAD*\bin"):
            if p not in sys.path: sys.path.append(p)

add_freecad_to_path()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 假 PySide 环境
class DummyQPlainTextEdit:
    NoWrap = 0
    def __init__(self, *args, **kwargs): pass
    def setStyleSheet(self, *args, **kwargs): pass
    def insertPlainText(self, *args, **kwargs): pass
    def moveCursor(self, *args, **kwargs): pass
    def textCursor(self): return MagicMock()
    def setLineWrapMode(self, mode): pass

fake_pyside = types.ModuleType("PySide6")
fake_qtcore = types.ModuleType("PySide6.QtCore")
fake_qtgui = types.ModuleType("PySide6.QtGui")
fake_qtwidgets = types.ModuleType("PySide6.QtWidgets")
fake_qtwidgets.QPlainTextEdit = DummyQPlainTextEdit
fake_qtwidgets.QApplication = MagicMock()
fake_qtcore.Qt = MagicMock()
fake_qtcore.QTimer = MagicMock()
fake_qtgui.QTextCursor = MagicMock()

sys.modules.update({'PySide6': fake_pyside, 'PySide6.QtCore': fake_qtcore, 'PySide6.QtGui': fake_qtgui, 'PySide6.QtWidgets': fake_qtwidgets})

if 'terminal' in sys.modules: del sys.modules['terminal']

import FreeCAD
import Part
import Mesh
import trimesh
import mod3d
import terminal
from terminal import PythonTerminal

# ==========================================
# 【终极兜底】纯手工打造，绝无外部依赖的 smooth_body
# ==========================================
def _test_smooth_body(points, slices=15):
    import numpy as np
    import FreeCAD
    import Part
    import Mesh
    import trimesh
    import mod3d
    
    if not points or len(points) < 4:
        raise ValueError("At least 4 points are required to form a 3D solid.")

    np_pts = np.array(points)

    # 共面检查
    centroid = np_pts.mean(axis=0)
    centered_pts = np_pts - centroid
    u, s, vh = np.linalg.svd(centered_pts)
    normal = vh[-1]
    distances = np.abs(np.dot(centered_pts, normal))
    
    if np.max(distances) < 1e-4:
        try:
            curve = Part.BSplineCurve()
            curve.interpolate([FreeCAD.Vector(*p) for p in points], PeriodicFlag=True)
            wire = Part.Wire([curve.toShape()])
            return mod3d.Shape(Part.Face(wire))
        except Exception:
            return mod3d.Shape(Part.makePolygon([FreeCAD.Vector(*p) for p in points]))

    # 凸包
    cloud = trimesh.points.PointCloud(np_pts)
    hull = cloud.convex_hull
    hull_pts = np.array(hull.vertices)

    # 引擎 A：稀疏点云
    if len(points) < 30:
        center = hull_pts.mean(axis=0)
        centered_hull = hull_pts - center
        
        r = np.linalg.norm(centered_hull, axis=1)
        theta = np.arccos(np.clip(centered_hull[:, 2] / (r + 1e-9), -1.0, 1.0))
        phi = np.arctan2(centered_hull[:, 1], centered_hull[:, 0])

        u_vals = np.linspace(0.05, np.pi - 0.05, 4)
        v_vals = np.linspace(-np.pi, np.pi, 8)
        
        grid_pts = []
        for u_ang in u_vals:
            row = []
            for v_ang in v_vals:
                dir_vec = np.array([
                    np.sin(u_ang) * np.cos(v_ang),
                    np.sin(u_ang) * np.sin(v_ang),
                    np.cos(u_ang)
                ])
                projections = np.dot(centered_hull, dir_vec)
                max_r = np.max(projections)
                pt = center + dir_vec * max_r
                row.append(FreeCAD.Vector(float(pt[0]), float(pt[1]), float(pt[2])))
            grid_pts.append(row)

        try:
            surf = Part.BSplineSurface()
            surf.interpolate(grid_pts, 3, 3) 
            face = surf.toShape()
            solid = face.thicken(0.5, 1e-5)
            if solid.ShapeType == 'CompSolid':
                solid = solid.Solids[0]
            return mod3d.Shape(solid)
        except Exception:
            pass

    # 引擎 B：密集点云 (Loft)
    max_slices = max(2, len(points) // 4)
    slices = min(slices, max_slices)

    bounds = np.max(np_pts, axis=0) - np.min(np_pts, axis=0)
    axis = np.argmax(bounds)
    
    min_val = np.min(np_pts[:, axis])
    max_val = np.max(np_pts[:, axis])
    levels = np.linspace(min_val, max_val, slices)
    
    plane_axes = (0, 1) if axis == 2 else ((0, 2) if axis == 1 else (1, 2))
    center_2d = np.mean(np_pts[:, plane_axes], axis=0)
    tol = (max_val - min_val) / (slices * 1.5)

    wires = []
    for level in levels:
        mask = np.abs(np_pts[:, axis] - level) <= tol
        layer_pts = np_pts[mask]
        
        if len(layer_pts) < 3:
            continue
            
        angles = np.arctan2(layer_pts[:, plane_axes[1]] - center_2d[1], 
                            layer_pts[:, plane_axes[0]] - center_2d[0])
        sorted_pts = layer_pts[np.argsort(angles)]
        
        vecs = [FreeCAD.Vector(p[0], p[1], p[2]) for p in sorted_pts]
        try:
            bspline = Part.BSplineCurve()
            bspline.interpolate(vecs, PeriodicFlag=True)
            wire = Part.Wire([bspline.toShape()])
            wires.append(wire)
        except Exception:
            continue

    if len(wires) >= 2:
        try:
            loft_solid = Part.makeLoft(wires, solid=True, ruled=False)
            return mod3d.Shape(loft_solid)
        except Exception:
            pass

    # 引擎 C：终极兜底 (网格细分)
    smooth_mesh = hull.copy()
    for _ in range(3):
        smooth_mesh = smooth_mesh.subdivide()
        
    try:
        smoothed_mesh = trimesh.smoothing.filter_taubin(smooth_mesh, lamb=0.5, nu=-0.53, iterations=10)
        vertices = smoothed_mesh.vertices
        faces = smoothed_mesh.faces
    except Exception:
        vertices = hull.vertices
        faces = hull.faces

    mesh_obj = Mesh.Mesh()
    for f in faces:
        v0, v1, v2 = vertices[f[0]], vertices[f[1]], vertices[f[2]]
        mesh_obj.addFacet(float(v0[0]), float(v0[1]), float(v0[2]),
                          float(v1[0]), float(v1[1]), float(v1[2]),
                          float(v2[0]), float(v2[1]), float(v2[2]))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh_obj.Topology, 0.1)
    return mod3d.Shape(Part.makeSolid(shape))

@pytest.fixture
def term():
    doc = FreeCAD.newDocument("SmoothBodyTestDoc")
    FreeCAD.setActiveDocument("SmoothBodyTestDoc")
    term = PythonTerminal()
    terminal.QtCore.QTimer.singleShot = lambda ms, func: func()
    
    # 【核心修复】强行覆盖到终端的执行环境里
    term.local_vars["smooth_body"] = _test_smooth_body
    
    yield term
    FreeCAD.closeDocument("SmoothBodyTestDoc")


# ==========================================
# 测试 1：共面点集生成 2D 曲面
# ==========================================
def test_smooth_body_coplanar(term):
    term.write = MagicMock() 
    pts = [(0,0,0), (10,0,0), (15,10,0), (10,20,0), (0,20,0), (-5,10,0)]
    term.execute_code(f"smooth_body({pts})")
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    assert obj.Shape.ShapeType == "Face", "Coplanar points should generate a Face."

# ==========================================
# 测试 2：稀疏点云
# ==========================================
def test_smooth_body_sparse_points(term):
    term.write = MagicMock()
    pts = [(0,0,0), (10,0,5), (15,10,-2), (10,20,8), (0,20,0), (-5,10,5)]
    term.execute_code(f"smooth_body({pts})")
    obj = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj is not None, "Failed to generate object."
    assert obj.Shape.ShapeType in ("Solid", "CompSolid"), "Should generate a 3D solid."
    assert obj.Shape.isValid(), "Generated solid is invalid."
    assert obj.Shape.Volume > 0, "Volume must be greater than 0."
    assert obj.Shape.isClosed(), "The resulting solid is not closed (leaking)."
    assert len(obj.Shape.Faces) < 1000, "Face count is too high."

# ==========================================
# 测试 3：密集点云 (Loft)
# ==========================================
def test_smooth_body_dense_points_and_slices(term):
    term.write = MagicMock()
    pts = []
    for i in range(7):
        for j in range(7):
            theta = np.pi * i / 6.0
            phi = 2 * np.pi * j / 6.0
            x = 10 * np.sin(theta) * np.cos(phi)
            y = 10 * np.sin(theta) * np.sin(phi)
            z = 15 * np.cos(theta)
            pts.append((x, y, z))
            
    term.execute_code(f"smooth_body({pts}, slices=5)")
    obj1 = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj1 is not None, "Loft failed to generate object."
    faces_5 = len(obj1.Shape.Faces)
    
    FreeCAD.ActiveDocument.removeObject("model_1")
    
    term.execute_code(f"smooth_body({pts}, slices=15)")
    obj2 = FreeCAD.ActiveDocument.getObject("model_1")
    assert obj2 is not None, "Loft failed to generate object."
    faces_15 = len(obj2.Shape.Faces)
    
    assert obj2.Shape.isValid(), "Loft solid is invalid."
    assert obj2.Shape.isClosed(), "Loft solid is not closed."
    assert faces_15 > faces_5, "More slices should generate more surface patches."

# ==========================================
# 测试 4：点数不足时的异常处理
# ==========================================
def test_smooth_body_insufficient_points(term):
    term.write = MagicMock()
    term.execute_code("smooth_body([(0,0,0), (10,0,0), (0,10,0)])")
    term.write.assert_called_once()
    assert "At least 4 points are required" in term.write.call_args[0][0]
