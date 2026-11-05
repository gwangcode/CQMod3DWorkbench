import FreeCAD
import Part

class NoiseFeature:
    def __init__(self, obj):
        obj.addProperty("App::PropertyLink", "Base", "Base", "Source object")
        obj.addProperty("App::PropertyFloat", "Density", "Noise", "Density").Density = 0.2
        obj.addProperty("App::PropertyFloat", "Smoothness", "Noise", "Smoothness").Smoothness = 2.0
        obj.addProperty("App::PropertyFloat", "Amplitude", "Noise", "Amplitude").Amplitude = 0.1
        obj.addProperty("App::PropertyInteger", "Seed", "Noise", "Random seed").Seed = 0
        obj.Proxy = self

    def execute(self, obj):
        if not obj.Base: return
        from mod3d.patch import Shape
        from mod3d.deformers import apply_noise
        
        base_shape = Shape(obj.Base.Shape)
        # 强制传入 seed，确保每次重算结果一致
        result = apply_noise(
            base_shape,
            density=obj.Density,
            smoothness=obj.Smoothness,
            amplitude=obj.Amplitude,
            seed=obj.Seed
        )
        obj.Shape = result.shape

class ViewProviderNoise:
    def __init__(self, vobj): vobj.Proxy = self
    def getIcon(self): return ":/icons/Tree_Part.svg"
    def attach(self, vobj): self.ViewObject = vobj
    def updateData(self, fp, prop): pass
    def onChanged(self, vp, prop): pass


class TwistFeature:
    def __init__(self, obj):
        obj.addProperty("App::PropertyLink", "Base", "Base", "Source object")
        obj.addProperty("App::PropertyFloat", "AngleX", "Twist", "Angle X").AngleX = 0.0
        obj.addProperty("App::PropertyFloat", "AngleY", "Twist", "Angle Y").AngleY = 0.0
        obj.addProperty("App::PropertyFloat", "AngleZ", "Twist", "Angle Z").AngleZ = 0.0
        obj.addProperty("App::PropertyInteger", "Sections", "Twist", "Sections").Sections = 30
        obj.Proxy = self

    def execute(self, obj):
        if not obj.Base: return
        from mod3d.patch import Shape
        from mod3d.deformers import brep_twist_z
        
        base_shape = Shape(obj.Base.Shape)
        if abs(obj.AngleX) < 1e-6 and abs(obj.AngleY) < 1e-6:
            result = brep_twist_z(base_shape.shape, obj.AngleZ, sections=obj.Sections)
            obj.Shape = result
        else:
            res = base_shape ^ [obj.AngleX, obj.AngleY, obj.AngleZ]
            obj.Shape = res.shape

class ViewProviderTwist:
    def __init__(self, vobj): vobj.Proxy = self
    def getIcon(self): return ":/icons/Tree_Part.svg"
    def attach(self, vobj): self.ViewObject = vobj
    def updateData(self, fp, prop): pass
    def onChanged(self, vp, prop): pass
