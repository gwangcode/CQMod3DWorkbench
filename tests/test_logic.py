import sys
import os
import importlib.util
import numpy as np
from unittest.mock import MagicMock

def test_is_vec_logic():
    original_modules = dict(sys.modules)
    try:
        mock_freecad = MagicMock()
        class MockVector: pass
        mock_freecad.Vector = MockVector
        sys.modules['FreeCAD'] = mock_freecad
        sys.modules['Part'] = MagicMock()
        sys.modules['Mesh'] = MagicMock()

        utils_path = os.path.join(os.path.dirname(__file__), '..', 'mod3d', 'utils.py')
        spec = importlib.util.spec_from_file_location("mod3d_utils_isolated", utils_path)
        mod3d_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod3d_utils)

        _is_vec = mod3d_utils._is_vec
        assert _is_vec([1, 2, 3], 3) is True
        assert _is_vec([1, 2], 3) is False
        assert _is_vec((1.0, 2.0, 3.0), 3) is True
        assert _is_vec(np.array([1, 2, 3]), 3) is True
        assert _is_vec(np.array(["a", "b", "c"]), 3) is False
        fake_vector = MockVector()
        assert _is_vec(fake_vector, 3) is True
        assert _is_vec(fake_vector, 2) is False
    finally:
        sys.modules.clear()
        sys.modules.update(original_modules)
