import pytest
import sys
import numpy as np
from unittest.mock import MagicMock

# Mock FreeCAD for pure logic tests
sys.modules['FreeCAD'] = MagicMock()
sys.modules['FreeCAD'].Vector = lambda x, y, z: (x, y, z)
sys.modules['Part'] = MagicMock()

from mod3d.utils import _is_vec

def test_is_vec_with_list():
    assert _is_vec([1, 2, 3], 3) is True
    assert _is_vec([1, 2], 3) is False

def test_is_vec_with_tuple():
    assert _is_vec((1.0, 2.0, 3.0), 3) is True

def test_is_vec_with_numpy():
    assert _is_vec(np.array([1, 2, 3]), 3) is True
    assert _is_vec(np.array([1, 2, 3.0]), 3) is True
    assert _is_vec(np.array(["a", "b", "c"]), 3) is False

def test_is_vec_with_freecad_vector():
    # Because FreeCAD.Vector is mocked to return a tuple
    assert _is_vec((1, 2, 3), 3) is True
