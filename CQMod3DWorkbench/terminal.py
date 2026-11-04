import FreeCAD
import FreeCADGui
import Part
from PySide import QtGui, QtCore
import sys
import traceback
import codeop  # 用于判断多行代码是否输入完整

try:
    from cq_mod3d import *
    from utils import show
except ImportError as e:
    FreeCAD.Console.PrintError(f"无法加载 cq_mod3d: {e}\n请确保它在 FreeCAD 的 Python 环境中已安装。\n")

class PythonTerminal(QtGui.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, 'Courier New', monospace;")
        
        self.local_vars = {
            "App": FreeCAD,
            "Gui": FreeCADGui,
            "Part": Part,
            "show": show
        }
        
        # 保存原来的 stdout 以便后续恢复
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        
        self.prompt = ">>> "
        self.continuation_prompt = "... "
        self.buffer = []  # 用于缓存多行代码
        
        self.insertPlainText(self.prompt)
        self.moveCursor(QtGui.QTextCursor.End)

    def write(self, text):
        """接收 print 的输出，加入防崩溃保护"""
        try:
            self.moveCursor(QtGui.QTextCursor.End)
            self.insertPlainText(text)
            self.moveCursor(QtGui.QTextCursor.End)
            QtGui.QApplication.processEvents()
        except RuntimeError:
            # 如果 Qt 对象已被销毁，忽略打印，防止 FreeCAD 崩溃
            pass

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            cursor.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
            
            line_text = cursor.selectedText()
            # 移除提示符
            current_prompt = self.prompt if not self.buffer else self.continuation_prompt
            code_line = line_text.replace(current_prompt, "")
            
            self.buffer.append(code_line)
            full_code = "\n".join(self.buffer)
            
            # 使用 codeop 判断代码是否完整（例如冒号结尾、未闭合括号）
            try:
                is_complete = codeop.compile_command(full_code, "<input>", "exec") is not None
            except (SyntaxError, ValueError):
                is_complete = True # 如果语法已经错了，直接扔去执行报错
            except OverflowError:
                is_complete = True

            if is_complete:
                self.insertPlainText("\n")
                if full_code.strip():
                    self.execute_code(full_code)
                self.buffer.clear()
                self.insertPlainText(self.prompt)
            else:
                # 代码未结束，换行继续输入
                self.insertPlainText("\n" + self.continuation_prompt)
                
            self.moveCursor(QtGui.QTextCursor.End)
        else:
            super().keyPressEvent(event)

    def execute_code(self, code):
        try:
            compiled_code = compile(code, "<terminal>", "exec")
            # 尝试执行并打印返回值
            exec(compiled_code, self.local_vars)
        except Exception:
            err_msg = traceback.format_exc()
            self.write(f"{err_msg}\n")
            
    def closeEvent(self, event):
        """面板关闭时，恢复系统的 stdout，防止崩溃"""
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        super().closeEvent(event)