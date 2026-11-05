import FreeCAD
import Part
from typing import Union, Tuple

def array_rect(part, nx: int, ny: int, spacing: Union[float, Tuple[float, float]]):
    dx, dy = (spacing, spacing) if isinstance(spacing, (int, float)) else spacing
    shapes = []
    for i in range(nx):
        for j in range(ny):
            s = part.copy()
            s.translate(FreeCAD.Vector(i * dx, j * dy, 0))
            shapes.append(s)
    return Part.makeCompound(shapes)

def array_polar(part, count: int, radius: float, angle: float = 360.0):
    shapes = []
    for i in range(count):
        deg = i * (angle / count)
        s = part.copy()
        s.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), deg)
        s.translate(FreeCAD.Vector(radius, 0, 0))
        shapes.append(s)
    return Part.makeCompound(shapes)