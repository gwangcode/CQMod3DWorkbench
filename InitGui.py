import FreeCAD
import FreeCADGui
import os
import sys


class Mod3DWorkbench(FreeCADGui.Workbench):
    MenuText = "Mod3D Terminal"
    ToolTip = "Interactive FreeCAD Python Terminal for Mod3D"

    def Initialize(self):
        # 唯一可靠的插件路径
        plugin_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "Mod3DWorkbench")

        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)

        if not os.path.exists(plugin_dir):
            FreeCAD.Console.PrintWarning(
                f"⚠️ [Mod3D] 插件目录不存在: {plugin_dir}\n"
                f"请检查是否将整个 Mod3DWorkbench 文件夹放到了 Mod 目录中。\n"
            )

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
