import pytest
import os
import sys
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock
import importlib.util

# 获取项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def test_package_xml_metadata():
    """测试 package.xml 的格式和关键元数据是否正确"""
    package_path = os.path.join(ROOT_DIR, "package.xml")
    assert os.path.exists(package_path), "❌ 根目录下缺少 package.xml 文件"

    try:
        tree = ET.parse(package_path)
        root = tree.getroot()
    except ET.ParseError as e:
        pytest.fail(f"❌ package.xml 格式损坏，无法解析: {e}")

    # 1. 检查 Maintainer 是否已填写
    maintainer = root.find("{https://wiki.freecad.org/Package_Metadata}maintainer")
    assert maintainer is not None, "❌ 缺少 <maintainer> 标签"
    name = maintainer.find("{https://wiki.freecad.org/Package_Metadata}name")
    assert name is not None and name.text.strip() != "", "❌ Maintainer 的名字不能为空"

    # 2. 检查 Classname 是否与代码一致
    classname = root.find(".//{https://wiki.freecad.org/Package_Metadata}classname")
    assert classname is not None, "❌ 缺少 <classname> 标签"
    assert classname.text == "Code3D", "❌ classname 必须与 InitGui.py 中注册的类名 'Code3D' 完全一致"

    # 3. 检查 Icon 路径是否已配置
    icon_node = root.find("{https://wiki.freecad.org/Package_Metadata}icon")
    assert icon_node is not None, "❌ 缺少 <icon> 标签"

def test_icon_file_exists():
    """测试图标文件是否真的存在于指定的路径"""
    icon_rel_path = "Resources/Icons/Code3D.svg"
    icon_abs_path = os.path.join(ROOT_DIR, icon_rel_path)
    
    assert os.path.exists(icon_abs_path), f"❌ 找不到图标文件: {icon_rel_path}。请检查文件是否已创建且路径拼写正确。"

def test_initgui_imports():
    """测试 InitGui.py 是否能正常被导入，且没有语法错误"""
    
    # ==========================================
    # 【核心修复】备份当前的模块环境，防止污染其他测试
    # ==========================================
    original_modules = dict(sys.modules)
    
    try:
        # Mock 必要的模块
        sys.modules['FreeCADGui'] = MagicMock()
        sys.modules['FreeCAD'] = MagicMock()
        sys.modules['PySide6'] = MagicMock()
        sys.modules['PySide6.QtWidgets'] = MagicMock()
        sys.modules['PySide6.QtCore'] = MagicMock()
        sys.modules['PySide6.QtGui'] = MagicMock()
        
        # 如果 FreeCADGui.Workbench 不存在，注入一个假的
        if not hasattr(sys.modules['FreeCADGui'], 'Workbench'):
            sys.modules['FreeCADGui'].Workbench = type('Workbench', (object,), {})

        initgui_path = os.path.join(ROOT_DIR, "InitGui.py")
        
        # 动态加载 InitGui.py
        spec = importlib.util.spec_from_file_location("InitGui_Test", initgui_path)
        initgui_module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(initgui_module)
        except Exception as e:
            pytest.fail(f"❌ InitGui.py 存在语法或导入错误: {e}")
            
        # 验证 Code3D 类是否存在
        assert hasattr(initgui_module, "Code3D"), "❌ InitGui.py 中找不到名为 'Code3D' 的类"
        
    finally:
        # ==========================================
        # 【核心修复】恢复原先的模块环境
        # ==========================================
        sys.modules.clear()
        sys.modules.update(original_modules)
