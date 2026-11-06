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

# ==========================================
# 【核心修复】恢复全局导入，确保类方法和外部测试能访问
# ==========================================
try:
    import mod3d
    from mod3d.shapes import Shape2d
    from mod3d.parametric import NoiseFeature, ViewProviderNoise, TwistFeature, ViewProviderTwist
    from utils import show
except ImportError as e:
    FreeCAD.Console.PrintError(f"Failed to load mod3d: {e}\n")


class PythonTerminal(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        
        self._consumed_targets = []
        self.model_counter = 1
        self.history = []
        self.history_index = 0
        self.prompt = ">>> "
        self.continuation_prompt = "... "
        self.buffer = []

        def runf(path):
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read().strip()
            if not code:
                return
            
            lines = code.split('\n')
            last_line = lines[-1].strip()
            
            if not last_line or last_line.startswith('#'):
                try:
                    exec(compile(code, path, 'exec'), self.local_vars)
                    FreeCAD.Console.PrintMessage(f"✅ Executed script: {path}\n")
                except Exception as e:
                    self.write(f"❌ Script error: {str(e)}\n")
                return

            body_code = '\n'.join(lines[:-1])
            
            try:
                if body_code.strip():
                    exec(compile(body_code, path, 'exec'), self.local_vars)
                self.execute_code(last_line)
                FreeCAD.Console.PrintMessage(f"✅ Executed script: {path}\n")
            except Exception as e:
                self.write(f"❌ Script error: {str(e)}\n")

        self.local_vars = {
            "App": FreeCAD, "Gui": FreeCADGui, "Part": Part,
            "part": self._part_func, "V": FreeCAD.Vector, "runf": runf,
        }
        if 'show' in globals(): self.local_vars["show"] = show
        if 'mod3d' in globals():
            self.local_vars["mod3d"] = mod3d
            for name in dir(mod3d):
                if not name.startswith("_"):
                    self.local_vars[name] = getattr(mod3d, name)

        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self

        self.insertPlainText(self.prompt)
        self.moveCursor(QtGui.QTextCursor.End)

    def _part_func(self, name):
        doc = FreeCAD.ActiveDocument
        if not doc: 
            raise ValueError("No active FreeCAD document.")
        obj = doc.getObject(name)
        if not obj:
            all_objs = [o.Name for o in doc.Objects]
            raise ValueError(f"Could not find an object named '{name}'. Current objects are: {', '.join(all_objs)}")
        if hasattr(obj, "Shape") and obj.Shape:
            self._consumed_targets.append(name)
            return mod3d.Shape(obj.Shape, doc_name=name)
        else:
            raise TypeError(f"Object '{name}' is not a valid geometry.")

    def _build_tree(self, node, doc):
        def get_next_name(base):
            final_name = base
            idx = 1
            while doc.getObject(final_name):
                final_name = f"{base}{idx:03d}"
                idx += 1
            return final_name

        if getattr(node, 'doc_name', None):
            return doc.getObject(node.doc_name)

        if node.op in ["fuse", "cut", "common"]:
            child_objs = [self._build_tree(c, doc) for c in node.children]
            if not all(child_objs): 
                raise ValueError("Failed to build tree: missing child objects")
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

        elif node.op == "transform":
            child_obj = self._build_tree(node.children[0], doc)
            t_type, data = node.transform_data
            
            if t_type == "translate":
                child_obj.Placement.Base = child_obj.Placement.Base + FreeCAD.Vector(*data)
                return child_obj
            elif t_type == "rotate":
                child_obj.Placement.Rotation = child_obj.Placement.Rotation * \
                    FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), math.degrees(data[0])) * \
                    FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), math.degrees(data[1])) * \
                    FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), math.degrees(data[2]))
                return child_obj
            else:
                new_obj = doc.addObject("Part::Feature", get_next_name("Feature"))
                new_obj.Shape = node.shape
                return new_obj

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

    def _is_brackets_balanced(self, code):
        stack = []
        in_string = None
        escape = False
        for char in code:
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if in_string:
                if char == in_string:
                    in_string = None
                continue
            if char in ('"', "'"):
                in_string = char
                continue
            if char in ('(', '[', '{'):
                stack.append(char)
            elif char in (')', ']', '}'):
                if not stack:
                    return True
                stack.pop()
        return len(stack) == 0

    def _clear_current_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        cursor.movePosition(QtGui.QTextCursor.Right, n=4) 
        cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        self.moveCursor(QtGui.QTextCursor.End)

    def _remove_last_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.moveCursor(QtGui.QTextCursor.End)

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        block = cursor.block()
        line_text = block.text()
        pos_in_block = cursor.positionInBlock()
        
        prompt_len = 0
        if line_text.startswith(">>> "): prompt_len = 4
        elif line_text.startswith("... "): prompt_len = 4

        if prompt_len > 0:
            if event.key() == QtCore.Qt.Key_Home and not event.modifiers():
                cursor.clearSelection()
                cursor.setPosition(block.position() + prompt_len)
                self.setTextCursor(cursor)
                return

            if event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
                if cursor.hasSelection():
                    sel_start = cursor.selectionStart()
                    sel_end = cursor.selectionEnd()
                    if event.key() == QtCore.Qt.Key_Left and sel_start <= block.position() + prompt_len:
                        cursor.setPosition(block.position() + prompt_len, QtGui.QTextCursor.MoveAnchor)
                        cursor.setPosition(sel_end, QtGui.QTextCursor.KeepAnchor)
                        self.setTextCursor(cursor)
                        return
                    elif event.key() == QtCore.Qt.Key_Right and sel_end < block.position() + prompt_len:
                        cursor.setPosition(block.position() + prompt_len, QtGui.QTextCursor.MoveAnchor)
                        cursor.setPosition(sel_start, QtGui.QTextCursor.KeepAnchor)
                        self.setTextCursor(cursor)
                        return
                else:
                    if event.key() == QtCore.Qt.Key_Left and pos_in_block <= prompt_len:
                        return

            if event.key() == QtCore.Qt.Key_Backspace:
                if not cursor.hasSelection() and pos_in_block <= prompt_len:
                    return
                if cursor.hasSelection() and cursor.selectionStart() <= block.position() + prompt_len:
                    cursor.setPosition(block.position() + prompt_len, QtGui.QTextCursor.MoveAnchor)
                    self.setTextCursor(cursor)
                    return

        if event.key() == QtCore.Qt.Key_U and event.modifiers() == QtCore.Qt.ControlModifier:
            self._clear_current_line()
            return
            
        if event.key() == QtCore.Qt.Key_Z and event.modifiers() == QtCore.Qt.ControlModifier:
            if self.buffer:
                self.buffer.pop()
                self._remove_last_line()
            else:
                self._clear_current_line()
            return

        if event.key() == QtCore.Qt.Key_Up:
            if self.history and not self.buffer:
                if self.history_index > 0:
                    self.history_index -= 1
                self._replace_current_line(self.history[self.history_index])
            return

        elif event.key() == QtCore.Qt.Key_Down:
            if self.history and not self.buffer:
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self._replace_current_line(self.history[self.history_index])
                else:
                    self.history_index = len(self.history)
                    self._replace_current_line("")
            return

        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.EndOfLine)
            self.setTextCursor(cursor)

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

            is_complete = False
            if event.modifiers() == QtCore.Qt.ShiftModifier:
                is_complete = False
            else:
                try: 
                    if codeop.compile_command(full_code, "<input>", "exec") is not None:
                        if self._is_brackets_balanced(full_code):
                            is_complete = True
                except (SyntaxError, ValueError): 
                    is_complete = True

            if is_complete:
                self.insertPlainText("\n")
                if full_code.strip(): 
                    if full_code.strip() not in self.history:
                        self.history.append(full_code.strip())
                    self.history_index = len(self.history)
                    self.execute_code(full_code)
                
                self.buffer.clear()
                if full_code.strip() not in ("clear", "cls"):
                    self.insertPlainText(self.prompt)
            else:
                self.insertPlainText("\n" + self.continuation_prompt)
                
            self.moveCursor(QtGui.QTextCursor.End)
        else:
            super().keyPressEvent(event)

    def _replace_current_line(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
        cursor.movePosition(QtGui.QTextCursor.Right, n=4) 
        cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(text)
        self.moveCursor(QtGui.QTextCursor.End)

    def execute_code(self, code):
        if code.strip() in ("clear", "cls"):
            self.clear()
            self.insertPlainText(self.prompt)
            self.moveCursor(QtGui.QTextCursor.End)
            return

        self._consumed_targets = []
        try:
            try:
                result = eval(compile(code, "<terminal>", "eval"), self.local_vars)
                
                is_shape = False
                raw_shape = None
                
                if 'Shape2d' in globals() and isinstance(result, Shape2d):
                    raw_shape = result.to_face()
                    is_shape = True
                elif 'mod3d' in globals() and isinstance(result, mod3d.Shape):
                    raw_shape = result.shape
                    is_shape = True
                elif isinstance(result, Part.Shape):
                    raw_shape = result
                    is_shape = True

                if is_shape:
                    consumed = list(dict.fromkeys(self._consumed_targets))
                    while FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.getObject(f"model_{self.model_counter}"):
                        self.model_counter += 1
                    next_name = f"model_{self.model_counter}"
                    self.model_counter += 1

                    def do_show():
                        doc = FreeCAD.ActiveDocument
                        if not doc:
                            docs = FreeCAD.listDocuments()
                            doc = list(docs.values())[0] if docs else FreeCAD.newDocument("Mod3D")
                            
                        try:
                            old_obj = doc.getObject(consumed[0]) if consumed else None
                            old_color = old_obj.ViewObject.ShapeColor if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None
                            old_transparency = old_obj.ViewObject.Transparency if old_obj and hasattr(old_obj, 'ViewObject') and old_obj.ViewObject else None

                            if not consumed:
                                new_obj = show(raw_shape, name=next_name)
                                doc.recompute()
                            else:
                                if 'Shape2d' in globals() and isinstance(result, Shape2d):
                                    new_obj = show(raw_shape, name=next_name)
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
                            self.write(f"❌ Build failed: {str(e)}\n")
                            
                    QtCore.QTimer.singleShot(10, do_show)
                elif result is not None:
                    self.write(repr(result) + "\n")
                    
            except SyntaxError:
                try: 
                    exec(compile(code, "<terminal>", "exec"), self.local_vars)
                except SyntaxError:
                    self.write("❌ Syntax error: Please check if parentheses and quotation marks are closed, or if the code format is correct.\n")
                except Exception as e:
                    self.write(f"❌ Execution error: {str(e)}\n")
                    
        except Exception as e:
            self.write(f"❌ Unknown error: {str(e)}\n")

    def closeEvent(self, event):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        super().closeEvent(event)
