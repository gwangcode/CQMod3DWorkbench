import numpy as np
import FreeCAD

def showx(part):
    if hasattr(part, "BoundBox"):
        # 纯 FreeCAD 显示
        if not FreeCAD.ActiveDocument:
            FreeCAD.newDocument()
        obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "Preview")
        obj.Shape = part
        FreeCAD.ActiveDocument.recompute()

def plothull(part, axis=True, origin_size=0.05, axis_length=None):
    showx(part)

def plot2d(shape2d, marker_size=5, grid=False):
    import matplotlib.pyplot as plt
    from .shapes import Shape2d
    if isinstance(shape2d, Shape2d): shape2d = [shape2d]
    plt.figure(figsize=(8, 8))
    for s in shape2d:
        v = s.vertices
        if len(v) and not np.allclose(v[0], v[-1]):
            v = np.vstack([v, v[0]])
        plt.plot(v[:,0], v[:,1], 'r-o', markersize=marker_size, linewidth=1)
    plt.xlabel('X'); plt.ylabel('Y'); plt.axis('equal')
    plt.grid(grid); plt.tight_layout(); plt.show()

def plot3d(shape3d):
    import matplotlib.pyplot as plt
    from .shapes import Shape3d
    if isinstance(shape3d, Shape3d): shape3d = [shape3d]
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    for s in shape3d:
        v = s.vertices
        ax.plot(v[:,0], v[:,1], v[:,2], 'b-o')
    ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_zlabel('Z')
    plt.show()