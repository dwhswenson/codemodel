import pytest

from codemodel.numpydoc_helper import *

def example_function(a, b):
    """Something.

    Parameters
    ----------
    a : int
        this is a
    b : float
        this is b
    """

class ExampleClass(object):
    __doc__ = example_function.__doc__

@pytest.mark.parametrize("obj", [ExampleClass, example_function])
def test_numpydoc_type_desc(obj):
    types, descs = numpydoc_type_desc(obj)
    assert types == ['int', 'float']
    assert descs == ['this is a', 'this is b']


def test_numpydoc_type_desc_fails_builtin():
    with pytest.raises(RuntimeError):
        numpydoc_type_desc(hash)
