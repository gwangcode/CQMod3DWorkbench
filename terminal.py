import FreeCAD
import FreeCADGui
import Part
import sys
import traceback
import codeop
import os

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui, QtWidgets

try:
    import mod3d
    from utils import show
except ImportError as e:
    FreeCAD.Console.PrintError(f"Failed to load mod3d: {e}\n")

class PythonTerminal(QtWidgets.QPlainTextEdit):
    # ... __init__, _part_func, write, keyPressEvent 保持不变 ...
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        self._consumed_targets = []
        self.model_counter = 1
        
        self.local_vars = {
            "App": FreeCAD, "Gui": FreeCADGui, "Part": Part, "show": show,
            "part": self._part_func, "mod3d": mod3d, "V": FreeCAD.Vector
        }
        if 'mod3d' in sys.modules:
            for name in dir(mod3d):
                if not name.startswith("_"): self.local_vars[name] = getattr(mod3d, name)
        
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        
        self.prompt = ">>> "
        self.continuation_prompt = "... "
        self.buffer = []
        self.insertPlainText(self.prompt)
        self.moveCursor(QtGui.QTextCursor.End)

    def _part_func(self, name):
        doc = FreeCAD.ActiveDocument
        if not doc: raise ValueError("没有活动的 FreeCAD 文档。")
        obj = doc.getObject(name)
        if not obj: 
            all_objs = [o.Name for o in doc.Objects]
            raise ValueError(f"找不到名为 '{name}' 的对象。当前对象有: {', '.join(all_objs)}")
        if hasattr(obj, "Shape") and obj.Shape:
            self._consumed_targets.append(name)
            return mod3d.Shape(obj.Shape, doc_name=name)
        else:
            raise TypeError(f"对象 '{name}' 不是有效的几何体。")

    def _build_tree(self, node, doc):
        def get_next_name(base):
            final_name = base
            idx = 1
            while doc.getObject(final_name):
                final_name = f"{base}{idx:03d}"
                idx += 1
            return final_name

        # 1. 如果是已有的文档对象，直接返回
        if getattr(node, 'doc_name', None):
            return doc.getObject(node.doc_name)

        # 2. 布尔运算节点
        if node.op in ["fuse", "cut", "common"]:
            child_objs = [self._build_tree(c, doc) for c in node.children]
            if not all(child_objs): raise ValueError("构建树失败：找不到子对象")

            if node.op == "fuse":
                new_obj = doc.addObject("Part::MultiFuse", get_next_name("Fusion"))
                new_obj.Shapes = child_objs
                return new_obj
            elif node.op == "cut":
                new_obj = doc.addObject("Part::Cut", get_next_name("Cut"))
                new_obj.Base = child_objs[0]
                new_obj.Tool = child_objs[1]
                return new_obj
            elif node.op == "common":
                new_obj = doc.addObject("Part::MultiCommon", get_next_name("Common"))
                new_obj.Shapes = child_objs
                return new_obj

        # 3. 变换节点（平移/旋转为原地修改，缩放等生成新节点）
        elif node.op == "transform":
            child_obj = self._build_tree(node.children[0], doc)
            transform_type, data = node.transform_data

            if transform_type == "translate":
                child_obj.Placement.Base = child_obj.Placement.Base + FreeCAD.Vector(*data)
                return child_obj
            elif transform_type == "rotate":
                child_obj.Placement.Rotation = child_obj.Placement.Rotation * FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), data[0]) \
                                               * FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), data[1]) \
                                               * FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), data[2])
                return child_obj
            else:
                new_obj = doc.addObject("Part::Feature", get_next_name("Feature"))
                new_obj.Shape = node.shape
                return new_obj

        # 4. 形变节点
        elif node.op:
            child_obj = self._build_tree(node.children[0], doc)
            new_obj = doc.addObject("Part::Feature", get_next_name(node.op.capitalize()))
            new_obj.Shape = node.shape
            new_obj.addProperty("App::PropertyLinkList", "Sources", "Base", "Source objects")
            new_obj.Sources = [child_obj]
            return new_obj

        # 5. 【核心魔法】原生参数化图元映射
        elif getattr(node, 'primitive_data', None):
            p_type = node.primitive_data["type"]
            p_params = node.primitive_data["params"]
            
            if p_type == "box":
                temp = doc.addObject("Part::Box", get_next_name("Box"))
                for k, v in p_params.items(): setattr(temp, k, v)
            elif p_type == "sphere":
                temp = doc.addObject("Part::Sphere", get_next_name("Sphere"))
                for k, v in p_params.items(): setattr(temp, k, v)
            elif p_type == "cylinder":
                temp = doc.addObject("Part::Cylinder", get_next_name("Cylinder"))
                for k, v in p_params.items(): setattr(temp, k, v)
            elif p_type == "cone":
                temp = doc.addObject("Part::Cone", get_next_name("Cone"))
                for k, v in p_params.items(): setattr(temp, k, v)
            elif p_type == "torus":
                temp = doc.addObject("Part::Torus", get_next_name("Torus"))
                for k, v in p_params.items(): setattr(temp, k, v)
            else:
                temp = doc.addObject("Part::Feature", get_next_name("Feature"))
                temp.Shape = node.shape
                
            if hasattr(temp, 'ViewObject') and temp.ViewObject:
                temp.ViewObject.Visibility = False
            return temp

        # 6. 普通的叶子节点
        temp = doc.addObject("Part::Feature", get_next_name("TempFeature"))
        temp.Shape = node.shape
        if hasattr(temp, 'ViewObject') and temp.ViewObject:
            temp.ViewObject.Visibility = False
        return temp

    # ... write, keyPressEvent, execute_code, closeEvent 保持不变 ...
