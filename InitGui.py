import FreeCAD
import FreeCADGui
import os
import sys
import subprocess
import threading
from PySide import QtGui, QtCore

def check_dependencies():
    try:
        import cadquery
        import cq_mod3d
        return True
    except ImportError:
        return False

def install_dependencies_async(main_window, on_success_callback):
    progress_msg = QtGui.QMessageBox(main_window)
    progress_msg.setWindowTitle("正在安装依赖")
    progress_msg.setText("首次运行 CQ Mod3D，正在从 GitHub/PyPI 自动安装必要的 Python 库...\n\n这可能需要几分钟时间，请耐心等待。")
    progress_msg.setStandardButtons(QtGui.QMessageBox.NoButton)
    progress_msg.show()
    QtGui.QApplication.processEvents()

    def _install():
        try:
            FreeCAD.Console.PrintMessage("开始安装依赖...\n")
            cmd = [
                sys.executable, "-m", "pip", "install",
                "cadquery",
                "git+https://github.com/gwangcode/cq_mod3d.git"
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(process.stdout.readline, ""):
                FreeCAD.Console.PrintMessage(line)
                if not line: break
            process.stdout.close()
            return_code = process.wait()
            
            def _on_finish():
                progress_msg.close()
                if return_code == 0:
                    QtGui.QMessageBox.information(main_window, "安装成功", "依赖安装成功！")
                    # 安装成功后，直接触发回调重新加载工作台
                    on_success_callback()
                else:
                    QtGui.QMessageBox.critical(main_window, "安装失败", "自动安装失败，请检查网络。")
            
            QtCore.QTimer.singleShot(0, _on_finish)
        except Exception as e:
            FreeCAD.Console.PrintError(f"安装过程出错: {str(e)}\n")
            QtCore.QTimer.singleShot(0, progress_msg.close)

    thread = threading.Thread(target=_install)
    thread.daemon = True
    thread.start()


class CQMod3DWorkbench(FreeCADGui.Workbench):
    MenuText = "CQ Mod3D"
    ToolTip = "在终端中直接使用 cq_mod3d 编写代码操作 FreeCAD Part"

    def Activated(self):
        # 实时检查依赖（不再依赖 Initialize 时的状态）
        if not check_dependencies():
            main_window = FreeCADGui.getMainWindow()
            reply = QtGui.QMessageBox.question(
                main_window, "缺少依赖", 
                "检测到缺少 cq_mod3d 及 CadQuery 依赖。\n是否现在自动联网安装？",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
            )
            if reply == QtGui.QMessageBox.Yes:
                # 传入回调函数，安装成功后自动再次调用 Activated 尝试加载
                install_dependencies_async(main_window, self.Activated)
            return

        # 加载终端面板
        try:
            # 强制重新加载模块，确保安装后立即生效
            if 'terminal' in sys.modules:
                import importlib
                importlib.reload(sys.modules['terminal'])
            from terminal import PythonTerminal
        except Exception as e:
            FreeCAD.Console.PrintError(f"无法加载终端模块: {e}\n")
            return

        main_window = FreeCADGui.getMainWindow()
        existing_dock = main_window.findChild(QtGui.QDockWidget, "CQMod3DTerminalDock")
        
        if existing_dock:
            existing_dock.show()
            return

        self.terminal = PythonTerminal()
        self.dock = QtGui.QDockWidget("CQ Mod3D 终端", main_window)
        self.dock.setObjectName("CQMod3DTerminalDock")
        self.dock.setWidget(self.terminal)
        
        main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock)

    def Deactivated(self):
        main_window = FreeCADGui.getMainWindow()
        dock = main_window.findChild(QtGui.QDockWidget, "CQMod3DTerminalDock")
        if dock:
            dock.hide()

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(CQMod3DWorkbench())