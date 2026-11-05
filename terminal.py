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
            
            # 【容错修复】清理行首的各种提示符
            code_line = line_text
            if code_line.startswith(">>> "):
                code_line = code_line[4:]
            elif code_line.startswith(">>>"):
                code_line = code_line[3:]
            elif code_line.startswith("... "):
                code_line = code_line[4:]
            elif code_line.startswith("..."):
                code_line = code_line[3:]
            
            # 自动纠错中文引号
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
                if isinstance(result, mod3d.Shape):
                    is_shape = True
                    raw_shape = result.shape
                elif isinstance(result, Part.Shape):
                    is_shape = True
                    raw_shape = result
                
                if is_shape:
                    consumed = list(set(self._consumed_targets))
                    old_obj = None
                    clean_name = ""
                    
                    old_label = ""
                    old_placement = None
                    old_color = None
                    old_transparency = None
                    
                    if consumed and not code.strip().startswith("show("):
                        host_name = consumed[0]
                        old_obj = FreeCAD.ActiveDocument.getObject(host_name)
                        
                        if old_obj:
                            old_label = old_obj.Label
                            old_placement = old_obj.Placement.copy()
                            if hasattr(old_obj, 'ViewObject') and old_obj.ViewObject:
                                old_color = old_obj.ViewObject.ShapeColor
                                old_transparency = old_obj.ViewObject.Transparency
                        
                        for name in consumed:
                            if FreeCAD.ActiveDocument.getObject(name):
                                FreeCAD.ActiveDocument.removeObject(name)
                        clean_name = host_name
                    else:
                        for name in consumed:
                            if FreeCAD.ActiveDocument.getObject(name):
                                FreeCAD.ActiveDocument.removeObject(name)
                        
                        while FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.getObject(f"model_{self.model_counter}"):
                            self.model_counter += 1
                        clean_name = f"model_{self.model_counter}"
                        self.model_counter += 1
                    
                    def do_show():
                        try:
                            new_obj = show(raw_shape, name=clean_name)
                            if old_obj and new_obj:
                                new_obj.Label = old_label
                                new_obj.Placement = old_placement
                                if hasattr(new_obj, 'ViewObject') and new_obj.ViewObject:
                                    if old_color: new_obj.ViewObject.ShapeColor = old_color
                                    if old_transparency is not None: new_obj.ViewObject.Transparency = old_transparency
                                FreeCAD.ActiveDocument.recompute()
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
