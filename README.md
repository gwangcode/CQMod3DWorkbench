# CQ Mod3D Workbench for FreeCAD

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/1446196752.svg)](https://doi.org/10.5281/zenodo.23964056)
[![CI](https://github.com/gwangcode/CQMod3DWorkbench/actions/workflows/ci.yml/badge.svg)](https://github.com/gwangcode/CQMod3DWorkbench/actions/workflows/ci.yml)

An interactive FreeCAD workbench that provides an embedded Python terminal with native support for **[cq_mod3d](https://github.com/gwangcode/cq_mod3d)** and **CadQuery**. 

Write Python code directly inside FreeCAD to generate procedural geometry, apply noise deformations, and manipulate FreeCAD Parts in real-time.

## ✨ Features

- **Embedded Python Terminal**: A fully functional, dark-themed Python console docked inside FreeCAD. Supports multi-line inputs and beautiful traceback error reporting.
- **Zero-Configuration Setup**: On first launch, if dependencies (`cadquery`, `cq_mod3d`) are missing, the workbench will prompt you to automatically install them via `pip` in the background. No manual environment configuration required!
- **Seamless Geometry Conversion**: Includes a built-in `show()` function that automatically converts CadQuery `Workplane` objects into FreeCAD `Part.Shape` objects (using temporary BREP files) and displays them in the active document.
- **Pre-injected Environment**: The terminal automatically imports `cq_mod3d as m3`, `cadquery as cq`, `FreeCAD as App`, and `Part`. You can use them immediately without writing import statements.

## 📦 Installation

### Method 1: Via FreeCAD Addon Manager (Recommended)
1. Open FreeCAD and go to **Tools → Addon Manager**.
2. Click the **Cogwheel icon** in the top right corner and select **Custom repositories**.
3. Add the following URL: `https://github.com/gwangcode/CQMod3DWorkbench`
4. Find **CQ Mod3D** in the list and click **Install**.
5. Restart FreeCAD.

### Method 2: Manual Installation via Git
1. Navigate to your FreeCAD `Mod` directory. (You can find this by opening the FreeCAD Python console and typing `App.getUserAppDataDir()`).
2. Clone this repository directly into the `Mod` folder:
   ```bash
   git clone https://github.com/gwangcode/CQMod3DWorkbench.git
   ```
3. Restart FreeCAD.

## 🚀 Usage

1. Open FreeCAD and create a new document.
2. Select **CQ Mod3D** from the Workbench dropdown menu at the top.
3. The **CQ Mod3D Terminal** will appear at the bottom of the screen. (If this is your first time, click "Yes" on the popup to automatically install dependencies).
4. Type Python code directly into the terminal and press `Enter`.

### Example Code

Try pasting these examples into the terminal:

**1. Create a basic CadQuery shape:**
```python
# Using the injected 'm3' (cq_mod3d) and 'show' functions
box = m3.cuboid(20, 20, 10) + [0, 0, 5]
show(box, "My_Box")
```

**2. Create a procedural noise rock:**
```python
# Generate a rough, rock-like sphere
rock = m3.apply_noise(m3.sphere(15), density=0.6, smoothness=1.5, amplitude=0.4)
show(rock, "My_Rock")
```

**3. Manipulate existing FreeCAD objects:**
```python
# Access the object you just created
obj = App.ActiveDocument.getObject("My_Rock")
print(f"Volume of the rock is: {obj.Shape.Volume}")
```

## ⚙️ How it works

The workbench intercepts `sys.stdout` to display print statements and errors directly in the custom PySide text widget. When you execute a command, it uses `exec()` within a pre-populated namespace. The `show()` function bridges the gap between CadQuery's OCCT geometry and FreeCAD's document structure by serializing to `.brep` format.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
