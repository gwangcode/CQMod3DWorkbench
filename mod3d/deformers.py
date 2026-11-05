# 在 deformers.py 顶部引入 Shape
from .patch import Shape

def apply_noise(part, density=0.2, smoothness=2.0, amplitude=0.1):
    # 如果传进来的是代理类，取出里面的真身
    raw_shape = part.shape if hasattr(part, "shape") else part
    
    # ... (保留你原有的 verts, faces, normals 计算逻辑) ...
    
    new_verts = verts + normals * (noise_vals[:, np.newaxis] * amplitude)
    final_shape = _tri_mesh_to_shape(new_verts, faces)
    
    # 【核心改造】返回带参数和子节点的 Shape 代理类！
    return Shape(final_shape, op="noise", children=[part], parameters={
        "density": density, "smoothness": smoothness, "amplitude": amplitude
    })
