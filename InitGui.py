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
            base_dir = os.path.dirname(exe)
            # 1. 优先找同目录或上级目录的 python.exe
            for name in ["python.exe", "pythonw.exe"]:
                candidates = [
                    os.path.join(base_dir, name),
                    os.path.join(os.path.dirname(base_dir), name),
                    os.path.join(os.path.dirname(base_dir), "bin", name)
                ]
                for c in candidates:
                    if os.path.exists(c):
                        return c, True
            # 2. 找不到 python.exe，退而求其次找 freecadcmd.exe
            cmd_exe = os.path.join(base_dir, "freecadcmd.exe")
            if os.path.exists(cmd_exe):
                return cmd_exe, False
        # 3. 兜底
        return exe, False

    def install_dependencies_async(self, main_window, on_success_callback):
        import subprocess
        import threading
        import tempfile
        import os
        import sys
        
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

        exe, is_python = self._get_python_exe()
        FreeCAD.Console.PrintMessage(f"Using interpreter: {exe}\n")
        
        script_path = None
        if is_python:
            # 如果是原生 python.exe，直接跑 -m pip
            cmd = [exe, "-m", "pip", "install", "cadquery", "git+https://github.com/gwangcode/cq_mod3d.git"]
        else:
            # 如果是 freecadcmd.exe，生成临时脚本让它执行
            script_content = """
import sys
try:
    from pip._internal.cli.main import main as pip_main
    sys.exit(pip_main(["install", "cadquery", "git+https://github.com/gwangcode/cq_mod3d.git"]))
except ImportError:
    try:
        import pip
        if hasattr(pip, 'main'):
            sys.exit(pip.main(["install", "cadquery", "git+https://github.com/gwangcode/cq_mod3d.git"]))
    except:
        pass
sys.exit(1)
"""
            temp_fd, script_path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(temp_fd, 'w') as f:
                f.write(script_content)
            cmd = [exe, script_path]
            
        kwargs = {}
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kwargs)

        def _reader():
            for line in iter(process.stdout.readline, ""):
                FreeCAD.Console.PrintMessage(line)
                if not line: break
            process.stdout.close()

        thread = threading.Thread(target=_reader)
        thread.daemon = True
        thread.start()

        timer = QtCore.QTimer()
        
        def check_process():
            if process.poll() is not None:
                timer.stop()
                progress_msg.close()
                if script_path and os.path.exists(script_path):
                    try:
                        os.unlink(script_path)
                    except:
                        pass
                
                if process.returncode == 0:
                    QtWidgets.QMessageBox.information(main_window, "Success", "Dependencies installed successfully!\nLoading terminal...")
                    on_success_callback()
                else:
                    QtWidgets.QMessageBox.critical(main_window, "Failed", f"Installation failed (code {process.returncode}).\nPlease check the Report View for details.")
            else:
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
