import FreeCAD
import FreeCADGui
import Part
import sys
import traceback
import codeop
import os
import math

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui, QtWidgets

try:
    import mod3d
    from mod3d.parametric import NoiseFeature, ViewProviderNoise, TwistFeature, ViewProviderTwist
    from utils import show
except ImportError as e:
    FreeCAD.Console.PrintError(f"Failed to load mod3d: {e}\n")

class PythonTerminal(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        self._consumed_targets = []
        self.model_counter = 1

        self.local_vars = {
            "App": FreeCAD, "Gui": FreeCADGui, "Part": Part, "show": show,
            "part": self._part_func, "mod3d": mod3d, "V": FreeCAD.Vector,
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
        if not doc: 
            raise ValueError("没有活动的 FreeCAD 文档。")
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

        # 1. 如果是已有文档的引用，直接返回
        if getattr(node, 'doc_name', None):
            return doc.getObject(node.doc_name)

        # 2. 布尔运算
        if node.op in ["fuse", "cut", "common"]:
            child_objs = [self._build_tree(c, doc) for c in node.children]
            if not all(child_objs): 
                raise ValueError("构建树失败：找不到子对象")
            if node.op == "fuse":
                new_obj = doc.addObject("Part::MultiFuse", get_next_name("Fusion"))
                new_obj.Shapes = child_objs
            elif node.op == "cut":
                new_obj = doc.addObject("Part::Cut", get_next_name("Cut"))
                new_obj.Base = child_objs[0]
                new_obj.Tool = child_objs[1]
            elif node.op == "common":
                new_obj = doc.addObject("Part::MultiCommon", get_next_name("Common"))
                new_obj.Shapes = child_objs
            return new_obj

        # 3. 空间变换（平移/旋转原地修改，缩放生成新节点）
        elif node.op == "transform":
            child_obj = self._build_tree(node.children[0], doc)
            t_type, data = node.transform_data
            
            if t_type == "translate":
                # 【核心语义】直接修改 Placement，不新建节点
                child_obj.Placement.Base = child_obj.Placement.Base + FreeCAD.Vector(*data)
                return child_obj
            elif t_type == "rotate":
                # 【核心修复】角度需转换为度
                child_obj.Placement.Rotation = child_obj.Placement.Rotation * \
                    FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), math.degrees(data[0])) * \
                    FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), math.degrees(data[1])) * \
                    FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), math.degrees(data[2]))
                return child_obj
            else:
                new_obj = doc.addObject("Part::Feature", get_next_name("Feature"))
                new_obj.Shape = node.shape
                return new_obj

        # 4. 参数化噪声
        elif node.op == "noise":
            child_obj = self._build_tree(node.children[0], doc)
            new_obj = doc.addObject("Part::FeaturePython", get_next_name("Noise"))
            NoiseFeature(new_obj)
            if hasattr(new_obj, 'ViewObject') and new_obj.ViewObject:
                ViewProviderNoise(new_obj.ViewObject)
            new_obj.Base = child_obj
            new_obj.Density = node.parameters.get("density", 0.2)
            new_obj.Smoothness = node.parameters.get("smoothness", 2.0)
            new_obj.Amplitude = node.parameters.get("amplitude", 0.1)
            new_obj.Seed = node.parameters.get("seed", 0)
            return new_obj

        # 4. 参数化扭转
        elif node.op == "twist":
            child_obj = self._build_tree(node.children[0], doc)
            new_obj = doc.addObject("Part::FeaturePython", get_next_name("Twist"))
            TwistFeature(new_obj)
            if hasattr(new_obj, 'ViewObject') and new_obj.ViewObject:
                ViewProviderTwist(new_obj.ViewObject)
            new_obj.Base = child_obj
            angles = node.parameters.get("angles", (0, 0, 0))
            new_obj.AngleX = angles[0]
            new_obj.AngleY = angles[1]
            new_obj.AngleZ = angles[2]
            new_obj.Sections = 30
            return new_obj

        # 5. 原生参数化图元
        elif getattr(node, 'primitive_data', None):
            p_type = node.primitive_data["type"]
            p_params = node.primitive_data["params"]
            obj_map = {"box": "Part::Box", "sphere": "Part::Sphere", "cylinder": "Part::Cylinder", "cone": "Part::Cone", "torus": "Part::Torus"}
            if p_type in obj_map:
                temp = doc.addObject(obj_map[p_type], get_next_name(p_type.capitalize()))
                for k, v in p_params.items(): setattr(temp, k, v)
            else:
                temp = doc.addObject("Part::Feature", get_next_name("Feature"))
                temp.Shape = node.shape
            if hasattr(temp, 'ViewObject') and temp.ViewObject:
                temp.ViewObject.Visibility = False
            return temp

        # 6. 兜底叶子节点
        temp = doc.addObject("Part::Feature", get_next_name("TempFeature"))
        temp.Shape = node.shape
        if hasattr(temp, 'ViewObject') and temp.ViewObject:
            temp.ViewObject.Visibility = False
        return temp

    def write(self, text):
        try:
            self.moveCursor(QtGui.QTextCursor.End)
            self.insertPlainText(text)
            self.moveCursor(QtGui.QTextCursor.End)
            QtWidgets.QApplication.processEvents()
        except RuntimeError: 
            pass

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
            code_line = cursor.selectedText()
            
            if code_line.startswith(">>> "): code_line = code_line[4:]
            elif code_line.startswith(">>>"): code_line = code_line[3:]
            elif code_line.startswith("... "): code_line = code_line[4:]
            elif code_line.startswith("..."): code_line = code_line[3:]
            
            code_line = code_line.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
            self.buffer.append(code_line)
            full_code = "\n".join(self.buffer)

            try: 
                is_complete = codeop.compile_command(full_code, "<input>", "exec") is not None
            except (SyntaxError, ValueError): 
                is_complete = True

            if is_complete:
                self.insertPlainText("\n")
                if full_code.strip(): 
                    self.execute_code(full_code)
                self.buffer.clear()
                self.insertPlainText(self.prompt)
            else:
                self.insertPlainText("\n" + self.continuation_prompt)
            self.moveCursor(QtGui.QTextCursor.End)
        else:
            super().keyPressEvent(event)

    def execute_code(self, code):
        self._consumed_targets = []
        try:
            try:
                result = eval(compile(code, "<terminal>", "eval"), self.local_vars)
                is_shape = isinstance(result, (mod3d.Shape, Part.Shape))
                
                if is_shape:
                    consumed = list(dict.fromkeys(self._consumed_targets))
                    while FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.getObject(f"model_{self.model_counter}"):
                        self.model_counter += 1
                    next_name = f"model_{self.model_counter}"
                    self.model_counter += 1

                    def do_show():
                        doc = FreeCAD.ActiveDocument
                        try:
                            old_obj = doc.getObject(consumed[0]) if consumed else None
                            old_color = old_obj.ViewObject.ShapeColor if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None
                            old_transparency = old_obj.ViewObject.Transparency if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None

                            if not consumed:
                                new_obj = show(result.shape if isinstance(result, mod3d.Shape) else result, name=next_name)
                                doc.recompute()
                            else:
                                root_obj = self._build_tree(result, doc)
                                consumed_objs = [doc.getObject(n) for n in consumed]
                                consumed_names = [obj.Name for obj in consumed_objs if obj]

                                if root_obj and root_obj.Name not in consumed_names:
                                    for obj in consumed_objs:
                                        if obj and hasattr(obj, 'ViewObject') and obj.ViewObject:
                                            obj.ViewObject.Visibility = False

                                if old_obj and root_obj and hasattr(root_obj, 'ViewObject') and root_obj.ViewObject:
                                    if old_color: root_obj.ViewObject.ShapeColor = old_color
                                    if old_transparency is not None: root_obj.ViewObject.Transparency = old_transparency
                                doc.recompute()
                        except Exception as e:
                            self.write(f"Show Error: {e}\n")
                            
                    QtCore.QTimer.singleShot(10, do_show)
                elif result is not None:
                    self.write(repr(result) + "\n")
            except SyntaxError:
                try: 
                    exec(compile(code, "<terminal>", "exec"), self.local_vars)
                except Exception: 
                    self.write(f"{traceback.format_exc()}\n")
        except Exception:
            self.write(f"{traceback.format_exc()}\n")

    def closeEvent(self, event):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        super().closeEvent(event)
