import FreeCAD
import Part

class NoiseFeature:
    """参数化噪声特征"""
    def __init__(self, obj):
        obj.addProperty("App::PropertyLink", "Base", "Base", "Source object")
        obj.addProperty("App::PropertyFloat", "Density", "Noise", "Density").Density = 0.2
        obj.addProperty("App::PropertyFloat", "Smoothness", "Noise", "Smoothness").Smoothness = 2.0
        obj.addProperty("App::PropertyFloat", "Amplitude", "Noise", "Amplitude").Amplitude = 0.1
        obj.Proxy = self

    def execute(self, obj):
        if not obj.Base: return
        # 延迟导入，防止循环依赖
        from .patch import Shape
        from .deformers import apply_noise
        
        # 将底层的 Base Shape 包装起来，并执行噪声计算
        base_shape = Shape(obj.Base.Shape)
        result = apply_noise(base_shape, density=obj.Density, smoothness=obj.Smoothness, amplitude=obj.Amplitude)
        obj.Shape = result.shape

class ViewProviderNoise:
    def __init__(self, vobj):
        vobj.Proxy = self
    def getIcon(self):
        return ":/icons/Tree_Part.svg" # 随便借用个原生图标
    def attach(self, vobj):
        self.ViewObject = vobj
    def updateData(self, fp, prop): pass
    def onChanged(self, vp, prop): pass


class TwistFeature:
    """参数化扭转特征"""
    def __init__(self, obj):
        obj.addProperty("App::PropertyLink", "Base", "Base", "Source object")
        obj.addProperty("App::PropertyFloat", "AngleX", "Twist", "Angle X (rad/unit)").AngleX = 0.0
        obj.addProperty("App::PropertyFloat", "AngleY", "Twist", "Angle Y (rad/unit)").AngleY = 0.0
        obj.addProperty("App::PropertyFloat", "AngleZ", "Twist", "Angle Z (rad/unit)").AngleZ = 0.0
        obj.Proxy = self

    def execute(self, obj):
        if not obj.Base: return
        from .patch import Shape
        from .deformers import brep_twist_z
        
        base_shape = Shape(obj.Base.Shape)
        # 如果是纯Z轴扭转，使用原生B-rep方法，极快
        if abs(obj.AngleX) < 1e-6 and abs(obj.AngleY) < 1e-6:
            result = brep_twist_z(base_shape.shape, obj.AngleZ)
            obj.Shape = result
        else:
            # 复杂扭转走代理类
            res = base_shape ^ [obj.AngleX, obj.AngleY, obj.AngleZ]
            obj.Shape = res.shape

class ViewProviderTwist:
    def __init__(self, vobj):
        vobj.Proxy = self
    def getIcon(self):
        return ":/icons/Tree_Part.svg"
    def attach(self, vobj):
        self.ViewObject = vobj
    def updateData(self, fp, prop): pass
    def onChanged(self, vp, prop): pass
