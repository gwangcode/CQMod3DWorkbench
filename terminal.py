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
                is_transform_op = False  # 判断是否为纯变换
                
                if isinstance(result, mod3d.Shape):
                    is_shape = True
                    raw_shape = result.shape
                    is_transform_op = getattr(result, "_is_transform", False)
                elif isinstance(result, Part.Shape):
                    is_shape = True
                    raw_shape = result
                    is_transform_op = False  # 原生的 Part.Shape 无法判断，统一当非破坏处理
                
                if is_shape:
                    consumed = list(dict.fromkeys(self._consumed_targets))
                    
                    while FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.getObject(f"model_{self.model_counter}"):
                        self.model_counter += 1
                    next_name = f"model_{self.model_counter}"
                    self.model_counter += 1
                    
                    def do_show():
                        doc = FreeCAD.ActiveDocument
                        try:
                            # 备份属性
                            old_obj = doc.getObject(consumed[0]) if consumed else None
                            old_color = old_obj.ViewObject.ShapeColor if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None
                            old_transparency = old_obj.ViewObject.Transparency if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None
                            old_label = old_obj.Label if old_obj else ""
                            old_placement = old_obj.Placement.copy() if old_obj else None

                            # ==========================================
                            # 【核心分流】：
                            # 1. 如果是平移/旋转/缩放 (is_transform_op=True)：删除原模型，原地替换。
                            # 2. 如果是布尔/变形/新建 (is_transform_op=False)：非破坏性，保留原模型。
                            # ==========================================
                            
                            if is_transform_op:
                                # 破坏性替换（纯变换）
                                host_name = consumed[0] if consumed else next_name
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
                                # 非破坏性（布尔/变形/纯新建）
                                # 1. 隐藏所有被消耗的原模型
                                for name in consumed:
                                    obj = doc.getObject(name)
                                    if obj and hasattr(obj, 'ViewObject') and obj.ViewObject:
                                        obj.ViewObject.Visibility = False
                                
                                # 2. 尽可能生成原生特征节点
                                if len(consumed) == 2 and code.count("part(") == 2:
                                    old_objs = [doc.getObject(n) for n in consumed if doc.getObject(n)]
                                    if "+" in code:
                                        new_obj = doc.addObject("Part::MultiFuse", next_name)
                                        new_obj.Shapes = old_objs
                                    elif "-" in code:
                                        new_obj = doc.addObject("Part::Cut", next_name)
                                        new_obj.Base = old_objs[0]
                                        new_obj.Tool = old_objs[1]
                                    elif "*" in code:
                                        new_obj = doc.addObject("Part::MultiCommon", next_name)
                                        new_obj.Shapes = old_objs
                                    else:
                                        new_obj = doc.addObject("Part::Feature", next_name)
                                        new_obj.Shape = raw_shape
                                else:
                                    new_obj = doc.addObject("Part::Feature", next_name)
                                    new_obj.Shape = raw_shape
                                
                                # 3. 继承属性
                                if old_obj:
                                    new_obj.Label = f"{old_label}_Op"
                                    if hasattr(new_obj, 'ViewObject') and new_obj.ViewObject:
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
