import pytest

try:
    import numpy as np
except ImportError:
    HAS_NUMPY = False
else:
    HAS_NUMPY = True
    from codemodel.type_validation.array_validation import *


@pytest.mark.parametrize("type_str, shape, dtype_str", [
    ("array((2,3), int)", (2,3), 'int'),
    ("array((2,), float)", (2,), 'float'),
    ("array(2, int32)", (2,), 'int32'),
    ("array((2, ...), int)", (2, ...), 'int'),
])
def test_parse_array_type(type_str, shape, dtype_str):
    np = pytest.importorskip("numpy")
    dtype = np.dtype(dtype_str)
    assert parse_array_type(type_str) == (shape, dtype)


@pytest.mark.parametrize("type_str", [
    "array", "array(2, int", "foo(2, int)", "array(int, 2)",
    "array(2, foo)", "array((2, 'foo'), int)",
])
def test_parse_array_type_errors(type_str):
    _ = pytest.importorskip("numpy")
    with pytest.raises(CodeModelTypeError):
        parse_array_type(type_str)


@pytest.mark.parametrize("type_str", [
    "array((2,3), int)", "array((2,), float)", "array(2, int32)",
    "array((2, ...), int)"
])
def test_is_array_type_true(type_str):
    assert is_array_type(type_str)

@pytest.mark.parametrize("type_str", [
    'int', 'str', 'foo', "array", "array(2, int", "foo(2, int)",
    "array(int, 2)", "array(2, foo)", "array((2, 'foo'), int)",
])
def test_is_array_type_false(type_str):
    assert not is_array_type(type_str)


class TestArrayTypeValidator(object):
    def setup(self):
        np = pytest.importorskip("numpy")
        self.validators = {
            'int_2_3': ArrayTypeValidator("array((2, 3), int)"),
            'int_2': ArrayTypeValidator("array(2, int)"),
            'int_e_3': ArrayTypeValidator("array((..., 3), int)"),
        }
        self.inputs = {
            'int_2_3': "[[1, 2, 3], [4, 5, 6]]",
            'int_2': "[1, 2]",
            'float_2_3': "[[3.1, 2.1, 1.1], [4.1, 5.1, 6.1]]",
            'int_3_3': "[[1, 2, 3], [4, 5, 6], [7, 8, 9]]",
        }
        self.arrays = {
            'int_2_3': np.array([[1, 2, 3], [4, 5, 6]], dtype='int'),
            'int_2' : np.array([1, 2], dtype='int'),
            'float_2_3': np.array([[1, 2, 3], [4, 5, 6]], dtype='float'),
            'int_3_3': np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                                dtype='int'),
        }
        self.valid_examples = {
            'int_2_3': ['int_2_3'],
            'int_2': ['int_2'],
            'int_e_3': ['int_2_3', 'int_3_3']
        }

    @pytest.mark.parametrize("name", ['int_2_3', 'int_2', 'int_e_3'])
    def test_to_instance(self, name):
        validator = self.validators[name]
        for case in self.valid_examples[name]:
            inst = validator.to_instance(self.inputs[case])
            np.testing.assert_array_equal(inst, self.arrays[case])

    @pytest.mark.parametrize("name", ['int_2_3', 'int_2', 'int_e_3'])
    def test_to_instance_errors(self, name):
        # apparently you can easily make an int dtype with float input
        # that's a numpy thing -- I'm not going to try to work around it
        exclude = {'float_2_3'}
        validator = self.validators[name]
        all_cases = set(self.inputs.keys())
        passing_cases = set(self.valid_examples[name])
        failing_cases = all_cases - passing_cases - exclude
        for case in failing_cases:
            with pytest.raises(ValueError):
                validator.to_instance(self.inputs[case])

    @pytest.mark.parametrize("name", ['int_2_3', 'int_2', 'int_e_3'])
    def test_is_valid(self, name):
        validator = self.validators[name]
        valid = set(self.valid_examples[name])
        not_valid = set(self.arrays.keys()) - valid
        for case in valid:
            assert validator.is_valid(self.arrays[case])

        for case in not_valid:
            assert not validator.is_valid(self.arrays[case])
        pass
