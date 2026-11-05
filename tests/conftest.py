import sys
import os
import glob

def add_freecad_to_path():
    """全局注入 FreeCAD 的路径，确保所有测试都能找到核心模块"""
    if 'CONDA_PREFIX' in os.environ:
        prefix = os.environ['CONDA_PREFIX']
        # 全面覆盖 Windows 和 Linux 的路径
        possible_paths = [
            os.path.join(prefix, 'lib'),                                # Linux
            os.path.join(prefix, 'lib', 'freecad', 'lib'),              # Linux
            os.path.join(prefix, 'lib', 'freecad', 'Mod'),              # Linux
            os.path.join(prefix, 'Library', 'lib'),                     # Windows
            os.path.join(prefix, 'Library', 'bin'),                     # Windows
            os.path.join(prefix, 'Lib', 'site-packages'),               # Windows
            os.path.join(prefix, 'bin'),                                # Windows
        ]
        for p in possible_paths:
            if os.path.exists(p) and p not in sys.path:
                sys.path.insert(0, p)
                
    if sys.platform == 'win32':
        # 补充搜索默认安装路径
        for p in glob.glob(r"C:\Program Files\FreeCAD*\bin") + glob.glob(r"C:\Program Files\FreeCAD*\lib"):
            if os.path.exists(p) and p not in sys.path:
                sys.path.insert(0, p)

# 在 pytest 收集任何测试之前执行
add_freecad_to_path()

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
