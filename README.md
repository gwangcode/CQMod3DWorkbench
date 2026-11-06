# Mod3D Workbench for FreeCAD

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/1446196752.svg)](https://doi.org/10.5281/zenodo.23964056)
[![CI](https://github.com/gwangcode/Mod3DWorkbench/actions/workflows/ci.yml/badge.svg)](https://github.com/gwangcode/Mod3DWorkbench/actions/workflows/ci.yml)

An interactive, zero-dependency FreeCAD workbench that provides an embedded Python terminal. It features a built-in geometry manipulation engine (Mod3D) that leverages **pure FreeCAD native `Part` APIs** to enable lightning-fast procedural modeling, real-time parameter updates, and non-destructive history trees.

Write Python code directly inside FreeCAD to generate geometry, apply noise deformations, and manipulate existing Parts in real-time.

## ✨ Features

- **🚀 Zero-Configuration & Blazing Fast**: No external CAD kernels (like CadQuery or OCP) to download. The terminal opens instantly.
- **💻 Embedded Python Terminal**: A fully functional, dark-themed Python console docked inside FreeCAD. Supports multi-line inputs, intelligent syntax checking, and error-proof prompt protection.
- **⚡ Operator Overloading Magic**: Directly use Python's math operators on FreeCAD shapes for rapid boolean operations, transformations, and deformations.
- **🔄 Non-Destructive Parametric Modeling**: All boolean operations and deformations preserve your original models. It automatically generates native FreeCAD nodes (e.g., `Fusion`, `Cut`, `Noise`, `Twist`) and hides the source objects. You can delete the new node at any time to recover the originals!
- **🧠 Real-Time Updates**: Because we generate native parametric nodes, modifying a base object (like changing a sphere's radius) will automatically cascade and update all downstream boolean or noise operations.
- **🪨 Procedural Noise**: Apply natural, rocky, or organic textures to regular geometries with a simple function call.
- **🖱️ Smart Object Picking**: Select any object in the FreeCAD tree and press `Ctrl + Shift + C` to instantly drop `part("object_name")` into the terminal.
- **📜 Script Execution**: Run external Python files directly in the terminal context using `runf("path/to/script.py")`.

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

**5. Execute an external script:**
```python
# Load and run a local .py file directly in the terminal
runf("D:/projects/my_complex_model.py")
```

---

## ⌨️ Terminal Shortcuts & Commands

Our terminal is designed to feel just like a native code REPL:

| Shortcut / Command | Action |
| :--- | :--- |
| `Up` / `Down` Arrows | Browse command history. |
| `Ctrl + U` | Clear the current input line. |
| `Ctrl + Z` | Undo multi-line input (step back to the previous line). |
| `Ctrl + Shift + C` | **(Macro)** Selected an object in the tree? Press this to inject `part("name")` into the terminal! |
| `Enter` | Execute the code (intelligently checks for unclosed brackets). |
| `Shift + Enter` | Force a new line without executing (enters `...` mode). |
| `clear` or `cls` | Clear the entire terminal screen. |
| `runf("path")` | Execute an external Python file in the terminal context. |

---

## 🧊 Built-in Primitives Library

The Mod3D engine comes with a rich set of built-in 3D and 2D primitives. All 3D primitives return a native `Part.Shape` wrapped in our magic operator proxy. 2D primitives return a `Shape2d` object which is automatically converted to a `Part.Face` for display.

### 3D Primitives

| Function Signature | Description |
| :--- | :--- |
| `cuboid(a=1, b=1, c=1)` | Creates a box with length `a`, width `b`, and height `c`. |
| `cube(a=1)` | Creates a cube with side length `a`. |
| `cylinder(radius=1, height=1)` | Creates a cylinder. |
| `cone(radius=1, height=1)` | Creates a cone with base radius and height. |
| `sphere(radius=1)` | Creates a sphere. |
| `torus(major_radius=2, minor_radius=1)` | Creates a torus (donut shape). |
| `ellipsoid(a=1, b=1, c=1)` | Creates an ellipsoid with semi-axes `a`, `b`, `c`. |
| `prism(radius=1, n=3, height=1)` | Creates a regular n-sided prism. |
| `pyramid(radius=1, n=3, height=1)` | Creates a regular n-sided pyramid. |
| `tetrahedron(a=1)` | Creates a tetrahedron (4 faces). |
| `octahedron(a=1)` | Creates an octahedron (8 faces). |
| `dodecahedron(a=1)` | Creates a dodecahedron (12 faces). |
| `icosahedron(a=1)` | Creates an icosahedron (20 faces). |
| `convex_hull(vertices)` | Creates a convex hull from a list of 3D points `[[x,y,z], ...]`. |
| `bspline_surface(points)` | Creates a closed B-spline surface from a list of 3D points or a 2D grid of points. |

**Example:**
```python
# Create a torus and rotate it
torus(20, 5) @ [1.57, 0, 0]
```

---

### 2D Primitives

2D primitives return a `Shape2d` object. They are automatically displayed as flat faces. To turn a 2D shape into a 3D solid, you can use the `.extrude()` method.

#### Standard 2D Shapes
| Function Signature | Description |
| :--- | :--- |
| `polygon(R=1, n=6)` | Regular n-sided polygon with circumradius `R`. |
| `circle(R=1, step=0.1)` | Circle with radius `R`. `step` controls segment density. |
| `rectangle(a=2, b=1)` | Rectangle with width `a` and height `b`. |
| `square(a=1)` | Square with side length `a`. |
| `parallelogram(a=1, b=1, angle=pi/4)` | Parallelogram with sides `a`, `b`, and angle. |
| `rhombus(a=1, angle=pi/4)` | Rhombus with side `a` and angle. |
| `trapezoid(upper_side=1, lower_side=2, height=1)` | Isosceles trapezoid. |
| `ellipse(a=2, b=1, step=0.1)` | Ellipse with semi-axes `a` and `b`. |

#### Regular Polygons
`pentagon(R=1)`, `hexagon(R=1)`, `heptagon(R=1)`, `octagon(R=1)`, `nonagon(R=1)`, `decagon(R=1)`.

#### Mathematical Curves
| Function Signature | Description |
| :--- | :--- |
| `parabola(a=1, b=2, w=1, step=0.1)` | Parabola curve. |
| `hyperbola(a=1, b=1, w=1, step=0.1)` | Hyperbola curve. |
| `spiral(a=1, b=1, num_turns=2, step=0.1)` | Archimedean spiral. |
| `cardioid(a=1, step=0.1)` | Cardioid (heart) curve. |
| `cycloid(a=1, num_cycles=2, step=0.1)` | Cycloid curve. |
| `astroid(a=1, step=0.1)` | Astroid (star) curve. |
| `catenary(a=1, step=0.1)` | Catenary (hanging chain) curve. |
| `epicycloid(R=10, r=1, step=0.1)` | Epicycloid curve. |
| `hypocycloid(R=6, r=1, step=0.1)` | Hypocycloid curve. |
| `lemniscate(a=1, step=0.1)` | Lemniscate (infinity) curve. |
| `semicircle(radius=1, step=0.1)` | Semicircle curve. |
| `sine(amplitude=1, frequency=1, x_start=0, x_end=2*pi, step=0.1)` | Sine wave. |
| `tangent(x_start=-0.5*pi, x_end=0.5*pi, step=0.1)` | Tangent curve. |

**Example: Creating a 3D shape from a 2D curve**
```python
# Create a 2D heart curve, convert it to a face, and extrude it into a 3D solid
heart_2d = cardioid(10)
heart_3d = heart_2d.to_face().extrude(V(0, 0, 5))
show(heart_3d, "Heart_Solid")
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
