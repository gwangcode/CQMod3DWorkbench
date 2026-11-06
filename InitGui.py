import FreeCAD
import FreeCADGui
import os
import sys

class Code3D(FreeCADGui.Workbench):
    MenuText = "Code3D Terminal"
    ToolTip = "Interactive FreeCAD Python Terminal for Code3D"
    
    # 绑定自定义图标
    Icon = os.path.join(os.path.dirname(__file__), "Resources", "Icons", "Code3D.svg")

    def Initialize(self):
        plugin_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "Code3D")
        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
        FreeCAD.Console.PrintMessage("🔥 Code3D Workbench Initialized\n")

    def Activated(self):
        try:
            from PySide6 import QtWidgets, QtCore, QtGui
        except ImportError:
            try:
                from PySide2 import QtWidgets, QtCore, QtGui
            except ImportError:
                from PySide import QtWidgets, QtCore, QtGui

        try:
            if 'terminal' in sys.modules:
                import importlib
                importlib.reload(sys.modules['terminal'])
            from terminal import PythonTerminal
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to load terminal module: {e}\n")
            return

        main_window = FreeCADGui.getMainWindow()
        existing_dock = main_window.findChild(QtWidgets.QDockWidget, "Code3DTerminalDock")
        
        if existing_dock:
            self.terminal = existing_dock.widget()
            existing_dock.show()
        else:
            self.terminal = PythonTerminal()
            self.dock = QtWidgets.QDockWidget("Code3D Terminal", main_window)
            self.dock.setObjectName("Code3DTerminalDock")
            self.dock.setWidget(self.terminal)
            main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock)

        if not hasattr(self, '_shortcut'):
            try:
                QShortcut = QtWidgets.QShortcut
            except AttributeError:
                QShortcut = QtGui.QShortcut
                
            self._shortcut = QShortcut(QtGui.QKeySequence("Ctrl+Shift+C"), main_window)
            self._shortcut.activated.connect(self._copy_selected_part)

    def _copy_selected_part(self):
        """Grab the selected object from the tree and copy part("name") to clipboard."""
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets

        sel = FreeCADGui.Selection.getSelection()
        if not sel:
            return
        
        name = sel[0].Name
        code = f'part("{name}")'
        
        # Copy to clipboard only
        try:
            QtWidgets.QApplication.clipboard().setText(code)
            FreeCAD.Console.PrintMessage(f"✅ Copied to clipboard: {code}\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to copy to clipboard: {e}\n")

    def Deactivated(self):
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets

        main_window = FreeCADGui.getMainWindow()
        dock = main_window.findChild(QtWidgets.QDockWidget, "Code3DTerminalDock")
        if dock:
            dock.hide()

    def GetClassName(self):
        return "Gui::PythonWorkbench"

# 注册改名后的类
FreeCADGui.addWorkbench(Code3D())
