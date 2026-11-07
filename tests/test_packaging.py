import pytest
import os
import sys
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock
import importlib.util

# 获取项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def find_tag(root, tag_name):
    """Helper to find tag with or without namespace"""
    ns = "{https://wiki.freecad.org/Package_Metadata}"
    node = root.find(f"{ns}{tag_name}")
    if node is None:
        node = root.find(tag_name)
    return node

def test_package_xml_metadata():
    """Test package.xml format and key metadata"""
    package_path = os.path.join(ROOT_DIR, "package.xml")
    assert os.path.exists(package_path), "❌ Missing package.xml in root directory"

    try:
        tree = ET.parse(package_path)
        root = tree.getroot()
    except ET.ParseError as e:
        pytest.fail(f"❌ package.xml is corrupted, unable to parse: {e}")

    # 1. Check Maintainer
    maintainer = find_tag(root, "maintainer")
    assert maintainer is not None, "❌ Missing <maintainer> tag"
    
    # Smart check: Support both <name> sub-tag or text content
    name_node = find_tag(maintainer, "name")
    if name_node is not None:
        maintainer_name = name_node.text
    else:
        maintainer_name = maintainer.text
        
    assert maintainer_name and maintainer_name.strip() != "", "❌ Maintainer name cannot be empty"
    
    # Smart check: Support both <email> sub-tag or email attribute
    email_node = find_tag(maintainer, "email")
    if email_node is not None:
        maintainer_email = email_node.text
    else:
        maintainer_email = maintainer.get("email")
        
    assert maintainer_email and maintainer_email.strip() != "", "❌ Maintainer email cannot be empty"

    # 2. Check Classname
    content_node = find_tag(root, "content")
    assert content_node is not None, "❌ Missing <content> tag"
    
    workbench_node = find_tag(content_node, "workbench")
    assert workbench_node is not None, "❌ Missing <workbench> tag"
    
    classname = find_tag(workbench_node, "classname")
    assert classname is not None, "❌ Missing <classname> tag"
    assert classname.text == "Code3D", "❌ classname must match the class registered in InitGui.py exactly ('Code3D')"

    # 3. Check Icon
    icon_node = find_tag(root, "icon")
    assert icon_node is not None, "❌ Missing <icon> tag"

def test_icon_file_exists():
    """Test if the icon file actually exists at the specified path"""
    icon_rel_path = "Resources/Icons/Code3D.svg"
    icon_abs_path = os.path.join(ROOT_DIR, icon_rel_path)
    
    assert os.path.exists(icon_abs_path), f"❌ Icon file not found at: {icon_rel_path}. Check if it has been created and spelled correctly."

def test_initgui_imports():
    """Test if InitGui.py can be imported without syntax errors"""
    
    original_modules = dict(sys.modules)
    
    try:
        sys.modules['FreeCADGui'] = MagicMock()
        sys.modules['FreeCAD'] = MagicMock()
        sys.modules['PySide6'] = MagicMock()
        sys.modules['PySide6.QtWidgets'] = MagicMock()
        sys.modules['PySide6.QtCore'] = MagicMock()
        sys.modules['PySide6.QtGui'] = MagicMock()
        
        if not hasattr(sys.modules['FreeCADGui'], 'Workbench'):
            sys.modules['FreeCADGui'].Workbench = type('Workbench', (object,), {})

        initgui_path = os.path.join(ROOT_DIR, "InitGui.py")
        spec = importlib.util.spec_from_file_location("InitGui_Test", initgui_path)
        initgui_module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(initgui_module)
        except Exception as e:
            pytest.fail(f"❌ InitGui.py contains syntax or import errors: {e}")
            
        assert hasattr(initgui_module, "Code3D"), "❌ Class 'Code3D' not found in InitGui.py"
        
    finally:
        sys.modules.clear()
        sys.modules.update(original_modules)
