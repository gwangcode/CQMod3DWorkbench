import FreeCAD
import FreeCADGui
import os
import sys

class Mod3DWorkbench(FreeCADGui.Workbench):
    MenuText = "Mod3D Terminal"
    ToolTip = "Interactive FreeCAD Python Terminal for Mod3D"

    def Initialize(self):
        # 确保插件目录在 sys.path 中，这样才能 import mod3d 和 terminal
        plugin_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "Mod3DWorkbench")
        if not os.path.exists(plugin_dir):
            plugin_dir = FreeCAD.getHomePath() + "Mod/Mod3DWorkbench"
        
        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
            
        FreeCAD.Console.PrintMessage("🔥 Mod3D Workbench Initialized\n")

    def Activated(self):
        try:
            from PySide6 import QtWidgets, QtCore
        except ImportError:
            try:
                from PySide2 import QtWidgets, QtCore
            except ImportError:
                from PySide import QtWidgets, QtCore

        try:
            # 强制重新加载，防止修改代码后不刷新
            if 'terminal' in sys.modules:
                import importlib
                importlib.reload(sys.modules['terminal'])
            from terminal import PythonTerminal
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to load terminal module: {e}\n")
            return

        main_window = FreeCADGui.getMainWindow()
        existing_dock = main_window.findChild(QtWidgets.QDockWidget, "Mod3DTerminalDock")
        
        if existing_dock:
            existing_dock.show()
            return

        self.terminal = PythonTerminal()
        self.dock = QtWidgets.QDockWidget("Mod 3D Terminal", main_window)
        self.dock.setObjectName("Mod3DTerminalDock")
        self.dock.setWidget(self.terminal)
        
        main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock)

    def Deactivated(self):
        try:
            from PySide6 import QtWidgets
        except ImportError:
            try:
                from PySide2 import QtWidgets
            except ImportError:
                from PySide import QtWidgets
                
        main_window = FreeCADGui.getMainWindow()
        dock = main_window.findChild(QtWidgets.QDockWidget, "Mod3DTerminalDock")
        if dock:
            dock.hide()

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(Mod3DWorkbench())
