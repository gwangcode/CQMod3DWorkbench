import FreeCAD
import FreeCADGui
import Part
import sys
import traceback
import codeop

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui, QtWidgets

try:
    import cadquery as cq
    import cq_mod3d
    from utils import show
except ImportError as e:
    FreeCAD.Console.PrintError(f"Failed to load cq_mod3d: {e}\n")

class PythonTerminal(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        
        # 用于记录被 part() 读取的对象的原名
        self._current_target = None
        
        self.local_vars = {
            "App": FreeCAD,
            "Gui": FreeCADGui,
            "Part": Part,
            "show": show,
            "part": self._part_func, # 绑定到类方法
            "cq": cq,
            "m3": cq_mod3d,
            "cq_mod3d": cq_mod3d
        }
        
        if 'cq_mod3d' in sys.modules:
            for name in dir(cq_mod3d):
                if not name.startswith("_"):
                    self.local_vars[name] = getattr(cq_mod3d, name)
        
        self.model_counter = 1
        
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
        """从 FreeCAD 获取对象，并记录下我们正在操作这个名字"""
        doc = FreeCAD.ActiveDocument
        if not doc: 
            raise ValueError("没有活动的 FreeCAD 文档。")
        obj = doc.getObject(name)
        if not obj: 
            raise ValueError(f"找不到名为 '{name}' 的对象。")
        
        if hasattr(obj, "Shape") and obj.Shape:
            import tempfile, os
            temp_fd, temp_path = tempfile.mkstemp(suffix=".brep")
            os.close(temp_fd)
            try:
                obj.Shape.exportBrep(temp_path)
                cq_shape = cq.importers.importBrep(temp_path).val()
                
                # 【核心魔法】在这里记下：用户正在引用它
                self._current_target = name 
                
                return cq.Workplane("XY").newObject([cq_shape])
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
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
            current_prompt = self.prompt if not self.buffer else self.continuation_prompt
            code_line = line_text.replace(current_prompt, "")
            
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
        # 每次执行前，清空目标记录
        self._current_target = None 
        
        try:
            try:
                result = eval(compile(code, "<terminal>", "eval"), self.local_vars)
                
                if isinstance(result, cq.Workplane):
                    # 检查 _part_func 是否被调用过并留下了记录
                    target_name = self._current_target 
                    
                    if target_name and FreeCAD.ActiveDocument.getObject(target_name):
                        # 覆盖模式：把之前的删掉，用原名建新的
                        FreeCAD.ActiveDocument.removeObject(target_name)
                        clean_name = target_name
                    else:
                        # 全新模式：自动生成 model_x
                        while FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.getObject(f"model_{self.model_counter}"):
                            self.model_counter += 1
                        clean_name = f"model_{self.model_counter}"
                        self.model_counter += 1
                    
                    def do_show():
                        try:
                            show(result, name=clean_name)
                        except Exception as e:
                            self.write(f"Show Error: {e}\n")
                            
                    QtCore.QTimer.singleShot(10, do_show)
                    
                elif result is not None:
                    self.write(repr(result) + "\n")
                    
            except SyntaxError:
                exec(compile(code, "<terminal>", "exec"), self.local_vars)
                
        except Exception:
            self.write(f"{traceback.format_exc()}\n")
            
    def closeEvent(self, event):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        super().closeEvent(event)
