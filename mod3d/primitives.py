import numpy as np
import FreeCAD
import Part
import Mesh
import MeshPart
import trimesh
from .shapes import Shape2d
from .patch import Shape

# ==========================================
# ---- 3D primitives ----
# ==========================================
def cuboid(a=1, b=1, c=1): return Shape(Part.makeBox(a, b, c))
def cube(a=1):              return cuboid(a, a, a)
def cylinder(radius=1, height=1): return Shape(Part.makeCylinder(radius, height))
def cone(radius=1, height=1):     return Shape(Part.makeCone(radius, 0, height))
def sphere(radius=1, face_index=3): return Shape(Part.makeSphere(radius))
def torus(major_radius=2, minor_radius=1, division=0.1):
    return Shape(Part.makeTorus(major_radius, minor_radius))

def ellipsoid(a=1, b=1, c=1, division=0.1):
    sphere_shape = Part.makeSphere(1.0)
    mat = FreeCAD.Matrix()
    mat.scale(a, b, c)
    return Shape(sphere_shape.transformGeometry(mat))

def prism(radius=1, n=3, height=1):
    pts = [FreeCAD.Vector(radius*np.cos(2*np.pi*i/n), radius*np.sin(2*np.pi*i/n), 0) for i in range(n)]
    pts.append(pts[0])
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    return Shape(face.extrude(FreeCAD.Vector(0, 0, height)))

def pyramid(radius=1, n=3, height=1, division=0.1):
    pts = [FreeCAD.Vector(radius*np.cos(2*np.pi*i/n), radius*np.sin(2*np.pi*i/n), 0) for i in range(n)]
    pts.append(pts[0])
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    return Shape(Part.makeLoft([face, Part.Vertex(FreeCAD.Vector(0, 0, height))], True))

def convex_hull(vertices):
    mesh = trimesh.convex.convex_hull(np.asarray(vertices, dtype=float))
    mesh_obj = Mesh.Mesh()
    for f in mesh.faces:
        v0, v1, v2 = mesh.vertices[f[0]], mesh.vertices[f[1]], mesh.vertices[f[2]]
        mesh_obj.addFacet(float(v0[0]), float(v0[1]), float(v0[2]),
                          float(v1[0]), float(v1[1]), float(v1[2]),
                          float(v2[0]), float(v2[1]), float(v2[2]))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh_obj.Topology, 0.1)
    return Shape(Part.makeSolid(shape))

def tetrahedron(a=1):
    return convex_hull([[0,0,0],[a,0,0], [0.5*a, 0.5*3**0.5*a, 0], [0.5*a, 0.5*a/3**0.5, 2**0.5/3**0.5*a]])

def octahedron(a=1):
    x = a / 2**0.5
    return convex_hull([[x,0,0],[-x,0,0],[0,x,0],[0,-x,0],[0,0,x],[0,0,-x]])

def dodecahedron(a=1):
    phi = 0.5*(1+5**0.5); c1 = 1/(3-phi)**0.5
    x1 = a*c1; x2, x3 = a*(c1/phi), a*(phi*c1)
    return convex_hull([
        [x1,x1,x1],[-x1,x1,x1],[x1,-x1,x1],[x1,x1,-x1],
        [-x1,-x1,x1],[-x1,x1,-x1],[x1,-x1,-x1],[-x1,-x1,-x1],
        [0,x2,x3],[0,-x2,x3],[0,x2,-x3],[0,-x2,-x3],
        [x2,x3,0],[-x2,x3,0],[x2,-x3,0],[-x2,-x3,0],
        [x3,0,x2],[-x3,0,x2],[x3,0,-x2],[-x3,0,-x2]])

def icosahedron(a=1):
    phi = 0.5*(1+5**0.5); x1 = a*0.5; x2 = x1*phi
    return convex_hull([
        [x1,x2,0],[-x1,x2,0],[x1,-x2,0],[-x1,-x2,0],
        [x2,0,x1],[-x2,0,x1],[x2,0,-x1],[-x2,0,-x1],
        [0,x1,x2],[0,-x1,x2],[0,x1,-x2],[0,-x1,-x2]])

# ==========================================
# ---- Advanced Surface & Point-Cloud Generators ----
# ==========================================
def bspline_surface(points, thickness=0.0):
    """
    Creates a closed B-spline surface from a 1D point list or a 2D grid of points.
    """
    if not points or len(points) == 0:
        raise ValueError("Point list cannot be empty.")

    is_1d = len(points[0]) == 3 and isinstance(points[0][0], (int, float))
    face = None
    
    if is_1d:
        vecs = [FreeCAD.Vector(p[0], p[1], p[2]) for p in points]
        curve = Part.BSplineCurve()
        curve.interpolate(vecs, PeriodicFlag=True)
        wire = Part.Wire([curve.toShape()])
        try:
            face = Part.Face(wire)
        except Exception:
            return Shape(wire, primitive_data={"type": "bspline_surface_1d", "params": {"points": points}})
    else:
        vecs_2d = [[FreeCAD.Vector(p[0], p[1], p[2]) for p in row] for row in points]
        surface = Part.BSplineSurface()
        surface.interpolate(vecs_2d)
        face = Part.Face(surface.toShape())

    if thickness > 0.0 and face is not None:
        try:
            solid = face.thicken(thickness, 1e-5)
            if solid.ShapeType == 'CompSolid':
                solid = solid.Solids[0]
            return Shape(solid)
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to thicken surface: {e}\n")
            return Shape(face)
    
    return Shape(face)


def smooth_body(points, slices=6):
    """
    Generate a minimal-face, mathematically smooth B-Spline body from unordered points.
    Algorithm: 
    1. Compute Convex Hull.
    2. Slice the hull into a few horizontal layers.
    3. Loft the sections into a solid.
    """
    import numpy as np
    
    if not points or len(points) < 4:
        raise ValueError("At least 4 points are required to form a 3D solid.")

    np_pts = np.array(points)

    # 1. Coplanarity check
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
            return Shape(Part.Face(wire))
        except Exception:
            return Shape(Part.makePolygon([FreeCAD.Vector(*p) for p in points]))

    hull = trimesh.convex.convex_hull(np_pts)
    mesh_obj = Mesh.Mesh()
    for f in hull.faces:
        v0, v1, v2 = hull.vertices[f[0]], hull.vertices[f[1]], hull.vertices[f[2]]
        mesh_obj.addFacet(float(v0[0]), float(v0[1]), float(v0[2]),
                          float(v1[0]), float(v1[1]), float(v1[2]),
                          float(v2[0]), float(v2[1]), float(v2[2]))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh_obj.Topology, 0.1)
    solid = Part.makeSolid(shape)

    bbox = solid.BoundBox
    lengths = [bbox.XLength, bbox.YLength, bbox.ZLength]
    axis = int(np.argmax(lengths))
    
    if axis == 0:
        normal_vec = FreeCAD.Vector(1, 0, 0)
        min_val, max_val = bbox.XMin, bbox.XMax
    elif axis == 1:
        normal_vec = FreeCAD.Vector(0, 1, 0)
        min_val, max_val = bbox.YMin, bbox.YMax
    else:
        normal_vec = FreeCAD.Vector(0, 0, 1)
        min_val, max_val = bbox.ZMin, bbox.ZMax

    margin = (max_val - min_val) * 0.01
    levels = np.linspace(min_val + margin, max_val - margin, slices)
    
    wires = []
    for level in levels:
        if axis == 0:
            plane = FreeCAD.Plane(origin=FreeCAD.Vector(level, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))
        elif axis == 1:
            plane = FreeCAD.Plane(origin=FreeCAD.Vector(0, level, 0), xDir=(1, 0, 0), normal=(0, 1, 0))
        else:
            plane = FreeCAD.Plane(origin=FreeCAD.Vector(0, 0, level), xDir=(1, 0, 0), normal=(0, 0, 1))
            
        sec = solid.section(plane)
        if sec and sec.Faces:
            main_face = max(sec.Faces, key=lambda f: f.Area)
            wires.append(main_face.outerWire())

    if len(wires) >= 2:
        try:
            loft_solid = Part.makeLoft(wires, solid=True, ruled=False)
            if loft_solid and loft_solid.isValid():
                return Shape(loft_solid)
        except Exception:
            pass
            
    smooth_mesh = hull.copy()
    for _ in range(2):
        smooth_mesh = smooth_mesh.subdivide()
    vertices = smooth_mesh.vertices
    faces = smooth_mesh.faces

    mesh_obj = Mesh.Mesh()
    for f in faces:
        v0, v1, v2 = vertices[f[0]], vertices[f[1]], vertices[f[2]]
        mesh_obj.addFacet(float(v0[0]), float(v0[1]), float(v0[2]),
                          float(v1[0]), float(v1[1]), float(v1[2]),
                          float(v2[0]), float(v2[1]), float(v2[2]))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh_obj.Topology, 0.1)
    return Shape(Part.makeSolid(shape))

# ==========================================
# ---- 2D primitives ----
# ==========================================
def polygon(R=1, n=6):
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    return Shape2d(np.column_stack([R*np.cos(t), R*np.sin(t)]))

def circle(R=1, step=0.1):
    return polygon(R, max(int(np.ceil(2*np.pi*R / step)), 20))

def rectangle(a=2, b=1):  return Shape2d([[0,0],[a,0],[a,b],[0,b]])
def square(a=1):          return rectangle(a, a)

def parallelogram(a=1, b=1, angle=np.pi/4):
    dx, dy = b*np.cos(angle), b*np.sin(angle)
    return Shape2d([[0,0],[a,0],[a+dx,dy],[dx,dy]])

def rhombus(a=1, angle=np.pi/4): return parallelogram(a, a, angle)

def trapezoid(upper_side=1, lower_side=2, height=1):
    x = (lower_side - upper_side) * 0.5
    return Shape2d([[0,0],[lower_side,0],[lower_side-x,height],[x,height]])

def pentagon(R=1):  return polygon(R, 5)
def hexagon(R=1):   return polygon(R, 6)
def heptagon(R=1):  return polygon(R, 7)
def octagon(R=1):   return polygon(R, 8)
def nonagon(R=1):   return polygon(R, 9)
def decagon(R=1):   return polygon(R, 10)

def ellipse(a=2, b=1, step=0.1):
    h = (a-b)**2 / (a+b)**2
    circ = np.pi*(a+b)*(1 + 3*h/(10 + np.sqrt(4-3*h)))
    n = max(int(np.ceil(circ / step)), 20)
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    return Shape2d(np.column_stack([a*np.cos(t), b*np.sin(t)]))

def parabola(a=1, b=2, w=1, step=0.1):
    x = np.linspace(-b, b, max(int(w / step), 20))
    return Shape2d(np.column_stack([x, x**2 / (4*a)]))

def hyperbola(a=1, b=1, w=1, step=0.1):
    n = max(int(4*a*np.arcsinh(b/a) / step), 20)
    t = np.linspace(-w*np.pi, w*np.pi, n)
    return Shape2d(np.column_stack([a*np.cosh(t), b*np.sinh(t)]))

def spiral(a=1, b=1, num_turns=2, step=0.1):
    L = num_turns*(np.sqrt(a*a + b*b) + a*np.arcsinh(b/a))
    t = np.linspace(0, 2*np.pi*num_turns, max(int(L/step), 20))
    return Shape2d(np.column_stack([a*t*np.cos(t), b*t*np.sin(t)]))

def cardioid(a=1, step=0.1):
    t = np.linspace(0, 2*np.pi, max(int(8*a/step), 20))
    return Shape2d(np.column_stack([a*(2*np.cos(t) - np.cos(2*t)), a*(2*np.sin(t) - np.sin(2*t))]))

def cycloid(a=1, num_cycles=2, step=0.1):
    t = np.linspace(0, 2*np.pi*num_cycles, max(int(8*a*num_cycles/step), 20))
    return Shape2d(np.column_stack([a*(t-np.sin(t)), a*(1-np.cos(t))]))

def astroid(a=1, step=0.1):
    t = np.linspace(0, 2*np.pi, max(int(6*a/step), 20))
    return Shape2d(np.column_stack([a*np.cos(t)**3, a*np.sin(t)**3]))

def catenary(a=1, step=0.1):
    t = np.linspace(-1, 1, max(int(a/step), 20))
    return Shape2d(np.column_stack([a*(np.cosh(t)-1), a*np.sinh(t)]))

def epicycloid(R=10, r=1, step=0.1):
    t = np.linspace(0, 2*np.pi, max(int(4*(R+r)/step), 20))
    return Shape2d(np.column_stack([
        (R+r)*np.cos(t) - r*np.cos((R+r)/r*t),
        (R+r)*np.sin(t) - r*np.sin((R+r)/r*t)]))

def hypocycloid(R=6, r=1, step=0.1):
    t = np.linspace(0, 2*np.pi, max(int(4*(R-r)/step), 20))
    return Shape2d(np.column_stack([
        (R-r)*np.cos(t) + r*np.cos((R-r)/r*t),
        (R-r)*np.sin(t) - r*np.sin((R-r)/r*t)]))

def lemniscate(a=1, step=0.1):
    t = np.linspace(0, 2*np.pi, max(int(8*a/step), 20))
    return Shape2d(np.column_stack([
        a*np.cos(t)/ (1 + np.sin(t)**2),
        a*np.cos(t)*np.sin(t)/ (1 + np.sin(t)**2)
    ]))

def semicircle(radius=1, step=0.1):
    t = np.linspace(0, np.pi, max(int(np.pi*radius/step), 20))
    return Shape2d(np.column_stack([radius*np.cos(t), radius*np.sin(t)]))

def sine(amplitude=1, frequency=1, x_start=0, x_end=2*np.pi, step=0.1):
    x = np.linspace(x_start, x_end, max(int((x_end-x_start)/step), 20))
    return Shape2d(np.column_stack([x, amplitude*np.sin(frequency*x)]))

def tangent(x_start=-0.5*np.pi, x_end=0.5*np.pi, step=0.1, height=100):
    x = np.linspace(x_start + 0.01, x_end - 0.01, max(int((x_end-x_start)/step), 20))
    y = np.tan(x)
    mask = np.abs(y) < height
    return Shape2d(np.column_stack([x[mask], y[mask]]))
