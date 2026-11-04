import FreeCAD
import FreeCADGui
import os
import sys
import subprocess
import threading

# 【终极兼容】动态判断 FreeCAD 使用的 PySide 版本 (兼容 0.19 到 1.0+)
try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui, QtWidgets

def install_dependencies_async(main_window, on_success_callback):
    progress_msg = QtWidgets.QMessageBox(main_window)
    progress_msg.setWindowTitle("Installing Dependencies")
    progress_msg.setText("First run of CQ Mod3D, auto-installing required Python libraries...\n\nThis may take a few minutes.")
    progress_msg.setStandardButtons(QtWidgets.QMessageBox.NoButton)
    progress_msg.show()
    QtWidgets.QApplication.processEvents()

    def _install():
        try:
            FreeCAD.Console.PrintMessage("Installing dependencies...\n")
            cmd = [sys.executable, "-m", "pip", "install", "cadquery", "git+https://github.com/gwangcode/cq_mod3d.git"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(process.stdout.readline, ""):
                FreeCAD.Console.PrintMessage(line)
                if not line: break
            process.stdout.close()
            return_code = process.wait()
            
            def _on_finish():
                progress_msg.close()
                if return_code == 0:
                    QtWidgets.QMessageBox.information(main_window, "Success", "Dependencies installed successfully!")
                    on_success_callback()
                else:
                    QtWidgets.QMessageBox.critical(main_window, "Failed", "Installation failed, please check your network.")
            QtCore.QTimer.singleShot(0, _on_finish)
        except Exception as e:
            FreeCAD.Console.PrintError(f"Installation error: {str(e)}\n")
            QtCore.QTimer.singleShot(0, progress_msg.close)

    thread = threading.Thread(target=_install)
    thread.daemon = True
    thread.start()

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

    def Activated(self):
        try:
            import cadquery
            import cq_mod3d
            has_deps = True
        except ImportError:
            has_deps = False

        if not has_deps:
            # 直接使用顶部已经兼容好的 QtWidgets，绝不再硬编码 PySide6
            reply = QtWidgets.QMessageBox.question(
                FreeCADGui.getMainWindow(), "Missing Dependencies", 
                "Missing cq_mod3d and CadQuery.\nInstall them automatically?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                install_dependencies_async(FreeCADGui.getMainWindow(), self.Activated)
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
        main_window = FreeCADGui.getMainWindow()
        dock = main_window.findChild(QtWidgets.QDockWidget, "CQMod3DTerminalDock")
        if dock:
            dock.hide()

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(CQMod3DWorkbench())
