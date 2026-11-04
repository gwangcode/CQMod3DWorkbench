import FreeCAD
import FreeCADGui
import os
import sys
import subprocess
import threading
from PySide import QtGui, QtCore

# 后台安装任务
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

    def Initialize(self):
        """FreeCAD 加载工作台时调用的方法"""
        # 核心修复：不用 __file__，直接用 FreeCAD 的 API 获取插件目录
        plugin_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "CQMod3DWorkbench")
        
        # 兼容部分旧版本或非默认安装路径（做个双重保险）
        if not os.path.exists(plugin_dir):
            plugin_dir = FreeCAD.getHomePath() + "Mod/CQMod3DWorkbench"
            
        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
            
        FreeCAD.Console.PrintMessage("🔥 CQ Mod3D 最新版代码加载成功！\n")

    def Activated(self):
        """用户点击工作台切换时调用的方法"""
        # 内联依赖检查
        try:
            import cadquery
            import cq_mod3d
            has_deps = True
        except ImportError:
            has_deps = False

        if not has_deps:
            main_window = FreeCADGui.getMainWindow()
            reply = QtGui.QMessageBox.question(
                main_window, "缺少依赖", 
                "检测到缺少 cq_mod3d 及 CadQuery 依赖。\n是否现在自动联网安装？",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
            )
            if reply == QtGui.QMessageBox.Yes:
                install_dependencies_async(main_window, self.Activated)
            return

        # 加载终端面板
        try:
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
        self.dock = QtGui.QDockWidget("CQ Mod 3D 终端", main_window)
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
