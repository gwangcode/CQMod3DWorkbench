import FreeCAD
import FreeCADGui
import Part
import sys
import traceback
import codeop
from PySide import QtCore, QtGui, QtWidgets

try:
    from cq_mod3d import *
    from utils import show
except ImportError as e:
    FreeCAD.Console.PrintError(f"Failed to load cq_mod3d: {e}\n")

class PythonTerminal(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace;")
        
        self.local_vars = {
            "App": FreeCAD,
            "Gui": FreeCADGui,
            "Part": Part,
            "show": show
        }
        
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
            compiled_code = compile(code, "<terminal>", "exec")
            exec(compiled_code, self.local_vars)
        except Exception:
            self.write(f"{traceback.format_exc()}\n")
            
    def closeEvent(self, event):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        super().closeEvent(event)
