import FreeCAD
import FreeCADGui

class CQMod3DWorkbench(FreeCADGui.Workbench):
    MenuText = "CQ Mod3D"
    ToolTip = "Interactive CadQuery terminal for FreeCAD"

    def Initialize(self):
        import os
        import sys
        plugin_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "CQMod3DWorkbench")
        if not os.path.exists(plugin_dir):
            plugin_dir = FreeCAD.getHomePath() + "Mod/CQMod3DWorkbench"
        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
        FreeCAD.Console.PrintMessage("🔥 CQ Mod3D Workbench Initialized\n")

    def _get_python_exe(self):
        import os
        import sys
        exe = sys.executable
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

    def install_dependencies_async(self, main_window, on_success_callback):
        import subprocess
        import threading
        
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

        python_exe = self._get_python_exe()
        FreeCAD.Console.PrintMessage(f"Using Python interpreter: {python_exe}\n")
        
        cmd = [python_exe, "-m", "pip", "install", "cadquery", "git+https://github.com/gwangcode/cq_mod3d.git"]
        
        kwargs = {}
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kwargs)

        # 用子线程去读 pip 的输出（这个子线程不碰 UI，所以是安全的）
        def _reader():
            for line in iter(process.stdout.readline, ""):
                FreeCAD.Console.PrintMessage(line)
                if not line: break
            process.stdout.close()

        thread = threading.Thread(target=_reader)
        thread.daemon = True
        thread.start()

        # 在主线程用 QTimer 轮询进程状态（完全符合 Qt 的规则）
        timer = QtCore.QTimer()
        
        def check_process():
            if process.poll() is not None:
                timer.stop()
                progress_msg.close()
                if process.returncode == 0:
                    QtWidgets.QMessageBox.information(main_window, "Success", "Dependencies installed successfully!\nLoading terminal...")
                    on_success_callback()
                else:
                    QtWidgets.QMessageBox.critical(main_window, "Failed", "Installation failed. Please check network.")
            else:
                # 让进度条保持呼吸
                QtWidgets.QApplication.processEvents()

        timer.timeout.connect(check_process)
        timer.start(100)

    def Activated(self):
        try:
            from PySide6 import QtWidgets, QtCore
        except Exception:
            try:
                from PySide2 import QtWidgets, QtCore
            except Exception:
                from PySide import QtWidgets, QtCore

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
            import sys
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
