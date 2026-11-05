# Mod3D Workbench for FreeCAD

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/1446196752.svg)](https://doi.org/10.5281/zenodo.23964056)
[![CI](https://github.com/gwangcode/Mod3DWorkbench/actions/workflows/ci.yml/badge.svg)](https://github.com/gwangcode/Mod3DWorkbench/actions/workflows/ci.yml)

An interactive, zero-dependency FreeCAD workbench that provides an embedded Python terminal. It features a built-in geometry manipulation engine (Mod3D) that leverages **pure FreeCAD native `Part` APIs** to enable lightning-fast procedural modeling, real-time parameter updates, and non-destructive history trees.

Write Python code directly inside FreeCAD to generate geometry, apply noise deformations, and manipulate existing Parts in real-time.

## ✨ Features

- **🚀 Zero-Configuration & Blazing Fast**: No external CAD kernels (like CadQuery or OCP) to download. The terminal opens instantly.
- **💻 Embedded Python Terminal**: A fully functional, dark-themed Python console docked inside FreeCAD. Supports multi-line inputs and beautiful traceback error reporting.
- **⚡ Operator Overloading Magic**: Directly use Python's math operators on FreeCAD shapes for rapid boolean operations, transformations, and deformations.
- **🔄 Non-Destructive Parametric Modeling**: All boolean operations and deformations preserve your original models. It automatically generates native FreeCAD nodes (e.g., `Fusion`, `Cut`, `Noise`, `Twist`) and hides the source objects. You can delete the new node at any time to recover the originals!
- **🧠 Real-Time Updates**: Because we generate native parametric nodes, modifying a base object (like changing a sphere's radius) will automatically cascade and update all downstream boolean or noise operations.
- **🪨 Procedural Noise**: Apply natural, rocky, or organic textures to regular geometries with a simple function call.

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

### 📢 Dependencies
This workbench runs entirely on FreeCAD's native `Part` module, so no heavy CAD kernels are required. However, `apply_noise`, `apply_noise_wire`, and 2D boolean operations rely on the following Python libraries:
- `numpy`
- `scipy`
- `trimesh`
- `shapely`

If your FreeCAD Python environment is missing any of them, install them via terminal:
```bash
pip install numpy scipy trimesh shapely
```

## 🚀 Usage

1. Open FreeCAD and create a new document.
2. Select **Mod3D Terminal** from the Workbench dropdown menu at the top.
3. The **Mod 3D Terminal** will appear at the bottom of the screen instantly.
4. Type Python code directly into the terminal and press `Enter`.

### Example Code

**1. Create basic shapes (Auto-named as `model_1`, `model_2`, etc.):**
```python
# Generate a cube and a sphere
cube(10)
sphere(6)
```

**2. Non-Destructive Boolean Operations (creates native `Cut`, `Fusion` nodes):**
```python
# Cut a sphere out of the cube.
# model_1 and model_2 will be hidden, a 'Cut' node is created.
part("model_1") - part("model_2")
```

**3. Destructive In-place Transformations:**
```python
# Move model_1 by 15mm in X. It updates in-place without creating new nodes.
part("model_1") + [15, 0, 0]
```

**4. Procedural Noise & Real-time Updates:**
```python
# Apply noise to the cube. This creates a parametric 'Noise' node.
# You can modify Density and Seed in the GUI's Data panel!
apply_noise(part("model_1"), density=0.6, smoothness=1.5, amplitude=0.4)
```

**5. Manipulate existing FreeCAD objects (even drawn via UI):**
```python
# If you drew a sketch and padded it named "BasePad", you can grab it like this:
part("BasePad") - sphere(5)
```

---

## ⚡ Operator Overloading Cheatsheet

Once a shape is created or retrieved via `part("name")`, you can use the following operators:

| Operator | Syntax Example | Operation | Effect on Tree / History |
| :--- | :--- | :--- | :--- |
| `+` | `shape + [x, y, z]` | **Translate (Positive)** | In-place update (Modifies Placement) |
| `+` | `shape1 + shape2` | **Boolean Union (Fuse)** | Non-destructive (Creates `Fusion` node) |
| `-` | `shape - [x, y, z]` | **Translate (Negative)** | In-place update (Modifies Placement) |
| `-` | `shape1 - shape2` | **Boolean Cut** | Non-destructive (Creates `Cut` node) |
| `*` | `shape * 2.0` | **Uniform Scale** | Generates new static feature |
| `*` | `shape * [2, 1, 0.5]` | **Non-uniform Scale** | Generates new static feature |
| `*` | `shape1 * shape2` | **Boolean Intersection** | Non-destructive (Creates `Common` node) |
| `@` | `shape @ [rx, ry, rz]` | **Rotation** (Radians) | In-place update (Modifies Placement) |
| `%` | `shape % [sxy, sxz, syx, syz, szx, szy]` | **Shear Transformation** | Generates new static feature |
| `^` | `shape ^ [ax, ay, az]` | **Twist** (Radians per unit) | Non-destructive (Creates `Twist` node) |

---

## ⚙️ How it works

The workbench intercepts `sys.stdout` to display print statements and errors directly in the custom PySide text widget. 

Under the hood, the `mod3d` package patches geometry operations to return an Abstract Syntax Tree (AST). When the terminal receives the final result, it recursively translates this AST into native FreeCAD parametric features (like `Part::MultiFuse`, `Part::Cut`, and custom `Part::FeaturePython` for noise/twist). This ensures you get the extreme flexibility of Python scripting combined with the robust parametric history of the FreeCAD GUI.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
