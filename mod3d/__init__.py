# mod3d/__init__.py
from .patch import Shape
from .shapes import Shape2d, Shape3d, solenoid
from .primitives import (
    cuboid, cube, cylinder, cone, sphere, torus, ellipsoid,
    prism, pyramid, convex_hull, tetrahedron, octahedron, dodecahedron, icosahedron,
    polygon, circle, rectangle, square, parallelogram, rhombus, trapezoid,
    pentagon, hexagon, heptagon, octagon, nonagon, decagon, ellipse,
    parabola, hyperbola, spiral, cardioid, cycloid, astroid, catenary,
    epicycloid, hypocycloid, lemniscate, semicircle, sine, tangent,
    bspline_surface
)
from .deformers import apply_noise, apply_noise_wire, brep_twist_z
from .operations import array_rect, array_polar
from .utils import extremes
from .vis import showx, plothull, plot2d, plot3d
