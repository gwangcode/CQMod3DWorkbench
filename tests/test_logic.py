import pytest
import sys
import numpy as np
from unittest.mock import MagicMock

def test_is_vec_logic():
    """独立测试 _is_vec 逻辑，完美隔离 FreeCAD 环境"""
    
    # 1. 保存当前的 sys.modules 状态
    original_modules = dict(sys.modules)
    
    try:
        # 2. 打桩所有相关模块（包括底层的 Mesh 和 MeshPart）
        sys.modules['FreeCAD'] = MagicMock()
        sys.modules['FreeCAD'].Vector = lambda x, y, z: (x, y, z)
        sys.modules['Part'] = MagicMock()
        sys.modules['Mesh'] = MagicMock()
        sys.modules['MeshPart'] = MagicMock()

        # 3. 在沙盒中导入函数
        from mod3d.utils import _is_vec
        
        # 4. 运行测试
        assert _is_vec([1, 2, 3], 3) is True
        assert _is_vec([1, 2], 3) is False
        assert _is_vec((1.0, 2.0, 3.0), 3) is True
        assert _is_vec(np.array([1, 2, 3]), 3) is True
        assert _is_vec(np.array([1, 2, 3.0]), 3) is True
        assert _is_vec(np.array(["a", "b", "c"]), 3) is False
        
        # 因为 FreeCAD.Vector 被 mock 成了返回 tuple 的 lambda
        assert _is_vec((1, 2, 3), 3) is True
        
    finally:
        # 5. 恢复 sys.modules，防止污染其他测试文件（比如 test_mod3d.py）
        sys.modules.clear()
        sys.modules.update(original_modules)
