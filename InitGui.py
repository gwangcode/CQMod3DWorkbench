import FreeCAD
import FreeCADGui
import os
import sys

class Mod3DWorkbench(FreeCADGui.Workbench):
    MenuText = "Mod3D Terminal"
    ToolTip = "Interactive FreeCAD Python Terminal for Mod3D"

    def Initialize(self):
        plugin_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "Mod3DWorkbench")
        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
        FreeCAD.Console.PrintMessage("🔥 Mod3D Workbench Initialized\n")

    def Activated(self):
        # 【核心修复】在这里动态导入 PySide，确保环境绝对就绪
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
        existing_dock = main_window.findChild(QtWidgets.QDockWidget, "Mod3DTerminalDock")
        
        if existing_dock:
            self.terminal = existing_dock.widget()
            existing_dock.show()
        else:
            self.terminal = PythonTerminal()
            self.dock = QtWidgets.QDockWidget("Mod 3D Terminal", main_window)
            self.dock.setObjectName("Mod3DTerminalDock")
            self.dock.setWidget(self.terminal)
            main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock)

        # 自动注册全局快捷键 Ctrl+Shift+C
        if not hasattr(self, '_shortcut'):
            self._shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+C"), main_window)
            self._shortcut.activated.connect(self._copy_selected_part)

    def _copy_selected_part(self):
        """抓取左侧选中的对象，并在终端当前光标处插入 part("name")"""
        sel = FreeCADGui.Selection.getSelection()
        if not sel:
            return
        
        name = sel[0].Name
        code = f'part("{name}")'
        
        if hasattr(self, 'terminal') and self.terminal:
            self.terminal.insertPlainText(code)
            self.terminal.setFocus()

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
