import sys
import os
import importlib.util
import numpy as np
from unittest.mock import MagicMock

def test_is_vec_logic():
    """独立测试 _is_vec 逻辑，完美隔离 FreeCAD 环境与模块缓存"""
    
    original_modules = dict(sys.modules)
    
    try:
        # 1. 伪造环境和 FreeCAD.Vector
        mock_freecad = MagicMock()
        class MockVector:
            pass
        mock_freecad.Vector = MockVector
        
        sys.modules['FreeCAD'] = mock_freecad
        sys.modules['Part'] = MagicMock()
        sys.modules['Mesh'] = MagicMock()

        # 2. 【核心修复】直接从文件路径加载 utils.py，避免触发 mod3d 包和缓存
        utils_path = os.path.join(os.path.dirname(__file__), '..', 'mod3d', 'utils.py')
        spec = importlib.util.spec_from_file_location("mod3d_utils_isolated", utils_path)
        mod3d_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod3d_utils)

        _is_vec = mod3d_utils._is_vec

        # 3. 运行测试
        assert _is_vec([1, 2, 3], 3) is True
        assert _is_vec([1, 2], 3) is False
        assert _is_vec((1.0, 2.0, 3.0), 3) is True
        assert _is_vec(np.array([1, 2, 3]), 3) is True
        assert _is_vec(np.array([1, 2, 3.0]), 3) is True
        assert _is_vec(np.array(["a", "b", "c"]), 3) is False
        
        # 测试传入模拟的 FreeCAD.Vector 实例
        fake_vector = MockVector()
        assert _is_vec(fake_vector, 3) is True
        assert _is_vec(fake_vector, 2) is False
        
    finally:
        # 4. 恢复环境
        sys.modules.clear()
        sys.modules.update(original_modules)
