# Mod3D Workbench for FreeCAD

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/1446196752.svg)](https://doi.org/10.5281/zenodo.23964056)
[![CI](https://github.com/gwangcode/Mod3DWorkbench/actions/workflows/ci.yml/badge.svg)](https://github.com/gwangcode/Mod3DWorkbench/actions/workflows/ci.yml)

An interactive, zero-dependency FreeCAD workbench that provides an embedded Python terminal. It features a built-in geometry manipulation engine (Mod3D) that leverages **pure FreeCAD native `Part` APIs** to enable lightning-fast procedural modeling and object manipulation directly inside your FreeCAD document.

Write Python code directly inside FreeCAD to generate geometry, apply noise deformations, and manipulate existing Parts in real-time.

## ✨ Features

- **🚀 Zero-Configuration & Blazing Fast**: No external dependencies (like CadQuery or OCP) to download. It runs 100% on FreeCAD's native `Part` module. The terminal opens instantly.
- **💻 Embedded Python Terminal**: A fully functional, dark-themed Python console docked inside FreeCAD. Supports multi-line inputs and beautiful traceback error reporting.
- **⚡ Operator Overloading Magic**: Directly use math-like operators on FreeCAD shapes!
  - `shape + [x, y, z]` for fast translation.
  - `shape1 + shape2` for Boolean union (fuse).
  - `shape1 - shape2` for Boolean cut.
  - `shape1 * shape2` for Boolean intersection.
  - `shape @ [rx, ry, rz]` for rotation.
- **🪨 Procedural Noise**: Apply natural, rocky, or organic textures to regular geometries with a simple function call.
- **🔄 Smart Object Replacement**: Type `part("model_1") - sphere(10)` and it will magically update `model_1` in-place, preserving its original color, label, and properties!

## 📦 Installation

### Method 1: Via FreeCAD Addon Manager (Recommended)
1. Open FreeCAD and go to **Tools → Addon Manager**.
2. Click the **Cogwheel icon** in the top right corner and select **Custom repositories**.
3. Add the following URL: `https://github.com/gwangcode/Mod3DWorkbench`
4. Find **Mod3D Workbench** in the list and click **Install**.
5. Restart FreeCAD.

### Method 2: Manual Installation via Git
1. Navigate to your FreeCAD `Mod` directory. (You can find this by opening the FreeCAD Python console and typing `App.getUserAppDataDir()`).
2. Clone this repository directly into the `Mod` folder:
   ```bash
   git clone https://github.com/gwangcode/Mod3DWorkbench.git
   ```
3. Restart FreeCAD.

## 🚀 Usage

1. Open FreeCAD and create a new document.
2. Select **Mod3D Terminal** from the Workbench dropdown menu at the top.
3. The **Mod 3D Terminal** will appear at the bottom of the screen instantly.
4. Type Python code directly into the terminal and press `Enter`.

### Example Code

Try pasting these examples into the terminal:

**1. Create basic shapes (Auto-named as `model_1`, `model_2`, etc.):**
```python
# Generate a cube and a sphere
cube(10)
sphere(6)
```

**2. Manipulate and Boolean operations using operators:**
```python
# Move model_1 by 15mm in X
part("model_1") + [15, 0, 0]

# Cut a sphere out of the cube (updates model_1 in-place!)
part("model_1") - sphere(6)
```

**3. Procedural Noise (Make a rock):**
```python
# Generate a rough, rock-like sphere
rock = apply_noise(sphere(15), density=0.6, smoothness=1.5, amplitude=0.4)
show(rock, "My_Rock")
```

**4. Manipulate existing FreeCAD objects (even drawn via UI):**
```python
# If you drew a sketch and padded it named "BasePad", you can grab it like this:
part("BasePad").cut(sphere(5))
```

## ⚙️ How it works

The workbench intercepts `sys.stdout` to display print statements and errors directly in the custom PySide text widget. When you execute a command, it uses `exec()` within a pre-populated namespace. 

The `mod3d` package internally patches `Part.Shape` to support Python's built-in math operators, meaning you can write extremely concise code like `box - sphere`. It bypasses file serialization entirely, performing all boolean and transformation operations directly in FreeCAD's C++ memory.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
