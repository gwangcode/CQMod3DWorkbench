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
        
        # 定义 part() 函数
        def part(name):
            doc = FreeCAD.ActiveDocument
            if not doc:
                raise ValueError("没有活动的 FreeCAD 文档。")
            obj = doc.getObject(name)
            if not obj:
                raise ValueError(f"找不到名为 '{name}' 的对象。")
            
            # 检查是否有几何形状
            if hasattr(obj, "Shape") and obj.Shape:
                # 将 FreeCAD 的 Shape 转换为 CadQuery 的 Workplane
                cq_shape = cq.Shape.cast(obj.Shape.wrapped)
                return cq.Workplane("XY").newObject([cq_shape])
            else:
                raise TypeError(f"对象 '{name}' 不是一个有效的几何体。")

        # 构建终端执行环境
        self.local_vars = {
            "App": FreeCAD,
            "Gui": FreeCADGui,
            "Part": Part,
            "show": show,
            "part": part, # 注入 part 函数
            "cq": cq,
            "m3": cq_mod3d,
            "cq_mod3d": cq_mod3d
        }
        
        # 注入 cq_mod3d 所有函数
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
        try:
            # 尝试单行 eval
            try:
                result = eval(compile(code, "<terminal>", "eval"), self.local_vars)
                
                if isinstance(result, cq.Workplane):
                    while FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.getObject(f"model_{self.model_counter}"):
                        self.model_counter += 1
                        
                    clean_name = f"model_{self.model_counter}"
                    self.model_counter += 1
                    
                    # 注意：这里去掉了 local_vars 的注入，完全依赖 part("名字") 机制
                    show(result, name=clean_name)
                    
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
