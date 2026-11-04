import FreeCAD
import FreeCADGui
import os
import sys
import subprocess
import threading

# 辅助函数：寻找 FreeCAD 自带的真正的 python.exe
def get_python_executable():
    exe = sys.executable
    # 如果 sys.executable 是 FreeCAD.exe，尝试找同目录或子目录下的 python.exe
    if "FreeCAD" in os.path.basename(exe):
        candidates = [
            os.path.join(os.path.dirname(exe), "python.exe"),
            os.path.join(os.path.dirname(exe), "bin", "python.exe"),
            os.path.join(sys.prefix, "bin", "python.exe"),
            os.path.join(sys.prefix, "python.exe")
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    return exe

class CQMod3DWorkbench(FreeCADGui.Workbench):
    MenuText = "CQ Mod3D"
    ToolTip = "Interactive CadQuery terminal for FreeCAD"

    def Initialize(self):
        plugin_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "CQMod3DWorkbench")
        if not os.path.exists(plugin_dir):
            plugin_dir = FreeCAD.getHomePath() + "Mod/CQMod3DWorkbench"
        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
        FreeCAD.Console.PrintMessage("🔥 CQ Mod3D Workbench Initialized\n")

    def install_dependencies_async(self, main_window, on_success_callback):
        try:
            from PySide6 import QtWidgets, QtCore
        except Exception:
            try:
                from PySide2 import QtWidgets, QtCore
            except Exception:
                from PySide import QtWidgets, QtCore

        progress_msg = QtWidgets.QMessageBox(main_window)
        progress_msg.setWindowTitle("Installing Dependencies")
        progress_msg.setText("First run of CQ Mod3D. Auto-installing required libraries...\n\nThis may take a few minutes.")
        progress_msg.setStandardButtons(QtWidgets.QMessageBox.NoButton)
        progress_msg.show()
        QtWidgets.QApplication.processEvents()

        def _install():
            # 【核心修复】在子线程内重新导入 PySide，防止闭包作用域丢失
            try:
                from PySide6 import QtCore
            except Exception:
                try:
                    from PySide2 import QtCore
                except Exception:
                    from PySide import QtCore
                    
            try:
                python_exe = get_python_executable()
                FreeCAD.Console.PrintMessage(f"Using Python interpreter: {python_exe}\n")
                
                cmd = [python_exe, "-m", "pip", "install", "cadquery", "git+https://github.com/gwangcode/cq_mod3d.git"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                
                for line in iter(process.stdout.readline, ""):
                    FreeCAD.Console.PrintMessage(line)
                    if not line: break
                    
                process.stdout.close()
                return_code = process.wait()
                
                def _on_finish():
                    progress_msg.close()
                    if return_code == 0:
                        # 再次动态导入，确保弹窗没问题
                        try:
                            from PySide6 import QtWidgets
                        except Exception:
                            try:
                                from PySide2 import QtWidgets
                            except Exception:
                                from PySide import QtWidgets
                        QtWidgets.QMessageBox.information(main_window, "Success", "Dependencies installed successfully!\nLoading terminal...")
                        on_success_callback()
                    else:
                        try:
                            from PySide6 import QtWidgets
                        except Exception:
                            try:
                                from PySide2 import QtWidgets
                            except Exception:
                                from PySide import QtWidgets
                        QtWidgets.QMessageBox.critical(main_window, "Failed", "Installation failed. Please check network.")
                
                QtCore.QTimer.singleShot(0, _on_finish)
            except Exception as e:
                FreeCAD.Console.PrintError(f"Installation error: {str(e)}\n")
                QtCore.QTimer.singleShot(0, progress_msg.close)

        thread = threading.Thread(target=_install)
        thread.daemon = True
        thread.start()

    def Activated(self):
        try:
            from PySide6 import QtWidgets
        except Exception:
            try:
                from PySide2 import QtWidgets
            except Exception:
                from PySide import QtWidgets

        try:
            import cadquery
            import cq_mod3d
            has_deps = True
        except ImportError:
            has_deps = False

        if not has_deps:
            self.install_dependencies_async(FreeCADGui.getMainWindow(), self.Activated)
            return

        try:
            if 'terminal' in sys.modules:
                import importlib
                importlib.reload(sys.modules['terminal'])
            from terminal import PythonTerminal
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to load terminal module: {e}\n")
            return

        main_window = FreeCADGui.getMainWindow()
        existing_dock = main_window.findChild(QtWidgets.QDockWidget, "CQMod3DTerminalDock")
        if existing_dock:
            existing_dock.show()
            return

        self.terminal = PythonTerminal()
        self.dock = QtWidgets.QDockWidget("CQ Mod 3D Terminal", main_window)
        self.dock.setObjectName("CQMod3DTerminalDock")
        self.dock.setWidget(self.terminal)
        main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock)

    def Deactivated(self):
        try:
            from PySide6 import QtWidgets
        except Exception:
            try:
                from PySide2 import QtWidgets
            except Exception:
                from PySide import QtWidgets
                
        main_window = FreeCADGui.getMainWindow()
        dock = main_window.findChild(QtWidgets.QDockWidget, "CQMod3DTerminalDock")
        if dock:
            dock.hide()

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(CQMod3DWorkbench())
