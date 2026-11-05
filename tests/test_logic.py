import pytest
import sys
import numpy as np
from unittest.mock import MagicMock

def test_is_vec_logic():
    """独立测试 _is_vec 逻辑，完美隔离 FreeCAD 环境"""
    
    # 1. 保存当前的 sys.modules 状态
    original_modules = dict(sys.modules)
    
    try:
        # 2. 打桩所有相关模块
        mock_freecad = MagicMock()
        # 【核心修复】用 type() 创建一个真实的类，这样才能通过 isinstance 检查
        mock_freecad.Vector = type('Vector', (object,), {})
        
        sys.modules['FreeCAD'] = mock_freecad
        sys.modules['Part'] = MagicMock()
        sys.modules['Mesh'] = MagicMock()

        # 3. 在沙盒中导入函数
        from mod3d.utils import _is_vec
        
        # 4. 运行测试
        assert _is_vec([1, 2, 3], 3) is True
        assert _is_vec([1, 2], 3) is False
        assert _is_vec((1.0, 2.0, 3.0), 3) is True
        assert _is_vec(np.array([1, 2, 3]), 3) is True
        assert _is_vec(np.array([1, 2, 3.0]), 3) is True
        assert _is_vec(np.array(["a", "b", "c"]), 3) is False
        
        # 测试传入模拟的 FreeCAD.Vector 实例
        fake_vector = sys.modules['FreeCAD'].Vector()
        assert _is_vec(fake_vector, 3) is True
        assert _is_vec(fake_vector, 2) is False
        
    finally:
        # 5. 恢复 sys.modules，防止污染其他测试文件
        sys.modules.clear()
        sys.modules.update(original_modules)
