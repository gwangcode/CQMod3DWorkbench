import numpy as np
import trimesh
import math
from scipy.ndimage import gaussian_filter, map_coordinates
import FreeCAD
import Part
from .utils import _tessellate, _tri_mesh_to_shape

# 注意：这里延迟导入 Shape 防止循环引用
def apply_noise(part, density=0.2, smoothness=2.0, amplitude=0.1):
    from .patch import Shape
    
    # 兼容纯 Part.Shape 和代理类
    raw_shape = part.shape if hasattr(part, "shape") else part
    
    verts, faces = _tessellate(raw_shape, tol=0.1)
    if len(verts) == 0: return part

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    normals = mesh.vertex_normals

    bounds = mesh.bounds
    padding = (bounds[1] - bounds[0]) * 0.1
    b_min = bounds[0] - padding
    b_max = bounds[1] + padding
    b_size = b_max - b_min

    grid_res = max(int(32 / max(density, 0.01)), 32)
    random_field = np.random.rand(grid_res, grid_res, grid_res)
    smoothed_field = gaussian_filter(random_field, sigma=max(smoothness, 0.1))

    indices = (verts - b_min) / b_size * (grid_res - 1)
    noise_vals = map_coordinates(smoothed_field, indices.T, order=1)
    noise_vals = (noise_vals - np.mean(noise_vals)) / (np.std(noise_vals) + 1e-6)
    noise_vals = np.clip(noise_vals, -2.0, 2.0) / 2.0

    new_verts = verts + normals * (noise_vals[:, np.newaxis] * amplitude)
    final_shape = _tri_mesh_to_shape(new_verts, faces)
    
    # 返回带有属性记录的代理类
    return Shape(final_shape, op="noise", children=[part], parameters={
        "density": density, "smoothness": smoothness, "amplitude": amplitude
    })

def apply_noise_wire(part, density=0.2, smoothness=2.0, amplitude=0.1):
    verts, _ = _tessellate(part.shape if hasattr(part, "shape") else part)
    if len(verts) == 0: return part
    bounds = [verts.min(axis=0), verts.max(axis=0)]
    b_size = bounds[1] - bounds[0]
    grid_res = max(int(32 / max(density, 0.01)), 32)
    
    random_field = np.random.rand(grid_res, grid_res, grid_res)
    smoothed_field = gaussian_filter(random_field, sigma=max(smoothness, 0.1))
    
    indices = (verts - bounds[0]) / (b_size + 1e-6) * (grid_res - 1)
    noise_vals = map_coordinates(smoothed_field, indices.T, order=1)
    noise_vals = (noise_vals - np.mean(noise_vals)) / (np.std(noise_vals) + 1e-6)
    noise_vals = np.clip(noise_vals, -2.0, 2.0) / 2.0

    offsets = np.random.randn(*verts.shape) * (noise_vals[:, np.newaxis] * amplitude)
    new_verts = verts + offsets

    vecs = [FreeCAD.Vector(v[0], v[1], v[2]) for v in new_verts]
    from .patch import Shape
    return Shape(Part.makePolygon(vecs), op="noise_wire", children=[part], parameters={"density": density, "smoothness": smoothness, "amplitude": amplitude})

def brep_twist_z(shape, az, sections=30):
    """纯 B-rep 沿 Z 轴扭转"""
    bbox = shape.BoundBox
    z_min, z_max = bbox.ZMin, bbox.ZMax
    height = z_max - z_min
    if height <= 0: return shape

    profiles = []
    for i in range(1, sections):
        t = i / sections
        z_level = z_min + t * height
        angle_deg = math.degrees(t * az * height)
        
        slice_wires = shape.slice(FreeCAD.Vector(0, 0, 1), z_level)
        if not slice_wires: continue
        
        face = Part.Face(slice_wires)
        face.rotate(FreeCAD.Vector(0, 0, z_level), FreeCAD.Vector(0, 0, 1), angle_deg)
        profiles.append(face)
        
    if len(profiles) >= 2:
        bot_faces = [f for f in shape.Faces if abs(f.BoundBox.ZMax - z_min) < 1e-5]
        top_faces = [f for f in shape.Faces if abs(f.BoundBox.ZMax - z_max) < 1e-5]
        
        if bot_faces and top_faces:
            bot = max(bot_faces, key=lambda f: f.Area)
            top = max(top_faces, key=lambda f: f.Area)
            
            bot.rotate(FreeCAD.Vector(0, 0, z_min), FreeCAD.Vector(0, 0, 1), 0)
            top.rotate(FreeCAD.Vector(0, 0, z_max), FreeCAD.Vector(0, 0, 1), math.degrees(az * height))
            
            profiles.insert(0, bot)
            profiles.append(top)
            try: return Part.makeLoft(profiles, True)
            except: pass
            
    # 降级网格法
    try:
        verts, faces = _tessellate(shape, tol=0.1)
        new_verts = np.empty_like(verts)
        for i, (x, y, z) in enumerate(verts):
            tz = az * z
            Rz = np.array([[np.cos(tz), -np.sin(tz), 0], [np.sin(tz),  np.cos(tz), 0], [0, 0, 1]])
            new_verts[i] = Rz @ np.array([x, y, z])
        return _tri_mesh_to_shape(new_verts, faces)
    except: return shape
