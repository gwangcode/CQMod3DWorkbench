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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        
        self._consumed_targets = []
        self.model_counter = 1
        
        self.local_vars = {
            "App": FreeCAD,
            "Gui": FreeCADGui,
            "Part": Part,
            "show": show,
            "part": self._part_func,
            "mod3d": mod3d,
            "V": FreeCAD.Vector
        }
        
        if 'mod3d' in sys.modules:
            for name in dir(mod3d):
                if not name.startswith("_"):
                    self.local_vars[name] = getattr(mod3d, name)
        
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
            raise ValueError(f"找不到名为 '{name}' 的对象。")
        
        if hasattr(obj, "Shape") and obj.Shape:
            self._consumed_targets.append(name)
            return mod3d.Shape(obj.Shape)
        else:
            raise TypeError(f"对象 '{name}' 不是一个有效的几何体。")

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
            
            line_text = cursor.selectedText()
            code_line = line_text
            if code_line.startswith(">>> "):
                code_line = code_line[4:]
            elif code_line.startswith(">>>"):
                code_line = code_line[3:]
            elif code_line.startswith("... "):
                code_line = code_line[4:]
            elif code_line.startswith("..."):
                code_line = code_line[3:]
            
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
                
                is_shape = False
                raw_shape = None
                is_transform_op = False
                
                if isinstance(result, mod3d.Shape):
                    is_shape = True
                    raw_shape = result.shape
                    is_transform_op = getattr(result, "_is_transform", False)
                elif isinstance(result, Part.Shape):
                    is_shape = True
                    raw_shape = result
                
                if is_shape:
                    consumed = list(dict.fromkeys(self._consumed_targets))
                    
                    def do_show():
                        doc = FreeCAD.ActiveDocument
                        try:
                            old_obj = doc.getObject(consumed[0]) if consumed else None
                            old_color = old_obj.ViewObject.ShapeColor if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None
                            old_transparency = old_obj.ViewObject.Transparency if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None
                            old_label = old_obj.Label if old_obj else ""
                            old_placement = old_obj.Placement.copy() if old_obj else None

                            if is_transform_op:
                                # 纯变换：原地替换
                                host_name = consumed[0] if consumed else "Unnamed"
                                if consumed:
                                    for name in consumed:
                                        if doc.getObject(name):
                                            doc.removeObject(name)
                                
                                new_obj = show(raw_shape, name=host_name)
                                if old_obj and new_obj:
                                    new_obj.Label = old_label
                                    if old_placement: new_obj.Placement = old_placement
                                    if hasattr(new_obj, 'ViewObject') and new_obj.ViewObject:
                                        if old_color: new_obj.ViewObject.ShapeColor = old_color
                                        if old_transparency is not None: new_obj.ViewObject.Transparency = old_transparency
                                    doc.recompute()
                                    
                            else:
                                # 非破坏性建模
                                for name in consumed:
                                    obj = doc.getObject(name)
                                    if obj and hasattr(obj, 'ViewObject') and obj.ViewObject:
                                        obj.ViewObject.Visibility = False
                                
                                # 如果涉及两个 part，优先使用 FreeCAD 原生的 Fusion / Cut / Common
                                if len(consumed) == 2 and code.count("part(") == 2:
                                    old_objs = [doc.getObject(n) for n in consumed if doc.getObject(n)]
                                    if "+" in code:
                                        new_obj = doc.addObject("Part::MultiFuse")
                                        new_obj.Shapes = old_objs
                                    elif "-" in code:
                                        new_obj = doc.addObject("Part::Cut")
                                        new_obj.Base = old_objs[0]
                                        new_obj.Tool = old_objs[1]
                                    elif "*" in code:
                                        new_obj = doc.addObject("Part::MultiCommon")
                                        new_obj.Shapes = old_objs
                                else:
                                    # 其他复杂操作（单模型变形、函数调用），生成带有来源属性的独立特征节点
                                    op_name = "Feature"
                                    if "apply_noise" in code: op_name = "Noise"
                                    elif "^" in code: op_name = "Twist"
                                    elif "array" in code: op_name = "Array"
                                    elif "@" in code: op_name = "Rotate"
                                    elif "*" in code: op_name = "Scale"
                                    
                                    new_obj = doc.addObject("Part::Feature", op_name)
                                    new_obj.Shape = raw_shape
                                    
                                    # 添加 Sources 属性，记录这步操作来源于哪些原模型
                                    if consumed:
                                        new_obj.addProperty("App::PropertyLinkList", "Sources", "Base", "Source objects")
                                        new_obj.Sources = [doc.getObject(n) for n in consumed if doc.getObject(n)]
                                
                                # 继承颜色
                                if old_obj and hasattr(new_obj, 'ViewObject') and new_obj.ViewObject:
                                    if old_color: new_obj.ViewObject.ShapeColor = old_color
                                    if old_transparency is not None: new_obj.ViewObject.Transparency = old_transparency
                                
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
