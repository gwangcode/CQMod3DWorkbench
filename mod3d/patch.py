# 找到 class Shape 的 __init__，修改为：
class Shape:
    def __init__(self, part_shape, is_transform=False, op=None, children=None, doc_name=None, transform_data=None, primitive_data=None, parameters=None):
        self.shape = part_shape
        self._is_transform = is_transform
        self.op = op                  
        self.children = children or [] 
        self.doc_name = doc_name      
        self.transform_data = transform_data 
        self.primitive_data = primitive_data 
        self.parameters = parameters or {} # 新增：记录具体参数

    # 修改 __xor__ 以记录参数：
    def __xor__(self, angles):
        if not _is_vec(angles, 3): raise ValueError("Twist expects 3 angles")
        ax, ay, az = _vec(angles)
        
        if abs(ax) < 1e-6 and abs(ay) < 1e-6:
            try:
                res = brep_twist_z(self.shape, az)
                if res is not None:
                    return Shape(res, op="twist", children=[self], parameters={"angles": angles})
            except Exception: pass
        # ... (下面的网格扭转同样加上 parameters={"angles": angles}) ...
