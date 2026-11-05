import numpy as np
import math
from scipy.ndimage import gaussian_filter, map_coordinates
import FreeCAD
import Part
import Mesh
import MeshPart
from .utils import _tessellate, _tri_mesh_to_shape

def brep_twist_z(part, az: float, sections: int = 30):
    """纯 B-rep 切片扭转"""
    bbox = part.BoundBox
    z_min, z_max = bbox.ZMin, bbox.ZMax
    height = z_max - z_min
    if height <= 0: return part

    profiles = []
    for i in range(1, sections):
        t = i / sections
        z_level = z_min + t * height
        angle_deg = math.degrees(t * az * height)
        
        # 获取切片
        slice_wires = part.slice(FreeCAD.Vector(0, 0, 1), z_level)
        if not slice_wires: continue
        
        face = Part.Face(slice_wires)
        face.rotate(FreeCAD.Vector(0, 0, z_level), FreeCAD.Vector(0, 0, 1), angle_deg)
        profiles.append(face)
        
    if len(profiles) >= 2:
        # 获取上下底面
        bot_faces = [f for f in part.Faces if abs(f.BoundBox.ZMax - z_min) < 1e-5]
        top_faces = [f for f in part.Faces if abs(f.BoundBox.ZMax - z_max) < 1e-5]
        
        if bot_faces and top_faces:
            bot = max(bot_faces, key=lambda f: f.Area)
            top = max(top_faces, key=lambda f: f.Area)
            
            bot.rotate(FreeCAD.Vector(0, 0, z_min), FreeCAD.Vector(0, 0, 1), 0)
            top.rotate(FreeCAD.Vector(0, 0, z_max), FreeCAD.Vector(0, 0, 1), math.degrees(az * height))
            
            profiles.insert(0, bot)
            profiles.append(top)
            
            try:
                return Part.makeLoft(profiles, True)
            except:
                pass

    # 降级网格法
    try:
        verts, faces = _tessellate(part, tol=0.1)
        new_verts = np.empty_like(verts)
        for i, (x, y, z) in enumerate(verts):
            tz = az * z
            Rz = np.array([[np.cos(tz), -np.sin(tz), 0], [np.sin(tz),  np.cos(tz), 0], [0, 0, 1]])
            new_verts[i] = Rz @ np.array([x, y, z])
        return _tri_mesh_to_shape(new_verts, faces)
    except Exception as e:
        FreeCAD.Console.PrintError(f"Twist failed: {e}\n")
        return part

def apply_noise(part, density: float = 0.2, smoothness: float = 2.0, amplitude: float = 0.1):
    verts, faces = _tessellate(part, tol=0.1)
    if len(verts) == 0: return part

    # 计算法线
    import trimesh
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
    return _tri_mesh_to_shape(new_verts, faces)

def apply_noise_wire(part, density: float = 0.2, smoothness: float = 2.0, amplitude: float = 0.1):
    verts, _ = _tessellate(part)
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

    # 生成 FreeCAD 连线
    vecs = [FreeCAD.Vector(v[0], v[1], v[2]) for v in new_verts]
    return Part.makePolygon(vecs)