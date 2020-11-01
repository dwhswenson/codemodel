import pytest
import ast

from codemodel.type_validation.type_validation import *

class TestTypeValidation(object):
    def setup(self):
        self.validation = TypeValidation([
            StandardValidatorFactory(STANDARD_TYPES_DICT)
        ])

    def test_register(self):
        validation = TypeValidation([])
        assert validation.factories == []
        factory = StandardValidatorFactory(STANDARD_TYPES_DICT)
        validation.register(factory)
        assert validation.factories == [factory]

    def test_getitem(self):
        assert self.validation._validators == {}
        int_val = self.validation['int']
        assert self.validation._validators == {'int': int_val}
        int_val_2 = self.validation['int']
        assert int_val is int_val_2  # idempotent

    def test_getitem_error(self):
        with pytest.raises(KeyError):
            self.validation['foo']


class ValidatorTester(object):
    def setup(self):
        self.factory = StandardValidatorFactory(STANDARD_TYPES_DICT)
        self.validator = self.factory.create(self.type_str)

    def test_validator(self):
        for val in self.good_values:
            assert self.validator.validate(val)

        for val in self.bad_values:
            assert not self.validator.validate(val)

    def test_raises_error(self):
        with pytest.raises(TypeError):
            self.validator.validate(self.obj)

    def test_is_valid(self):
        assert self.validator.is_valid(self.obj)

    def test_factory_is_my_type(self):
        assert self.factory.is_my_type(self.type_str)

    def test_factory_bad_type(self):
        assert not self.factory.is_my_type("foo")


class TestIntValidation(ValidatorTester):
    def setup(self):
        self.type_str = 'int'
        self.good_values = ["5"]
        self.bad_values = ["5.1", "Five"]
        self.obj = 5
        super().setup()

    def test_ast(self):
        expected = ast.Num(5)
        result = self.validator.to_ast("5")
        assert isinstance(result, ast.Num)
        assert result.n == expected.n


class TestFloatValidation(ValidatorTester):
    def setup(self):
        self.type_str = 'float'
        self.good_values = ["5", "5.1"]
        self.bad_values = ["Five"]
        self.obj = 5.1
        super().setup()

    def test_ast(self):
        expected = ast.Num(5.1)
        result = self.validator.to_ast("5.1")
        assert isinstance(result, ast.Num)
        assert result.n == expected.n


class TestStringValidation(ValidatorTester):
    def setup(self):
        self.type_str = 'str'
        self.good_values = ["5", "5.1", "Five"]
        self.bad_values = []
        self.obj = "Five"
        super().setup()

    def test_ast(self):
        expected = ast.Str("Five")
        result = self.validator.to_ast("Five")
        assert isinstance(result, ast.Str)
        assert result.s == expected.s

    def test_raises_error(self):
        pass  # strings don't raise errors!

class TestBoolValidation(ValidatorTester):
    def setup(self):
        self.factory = BoolValidator()
        self.validator = self.factory
        self.type_str = 'bool'
        self.good_values = [True, False]
        try:
            import numpy as np
        except ImportError:
            pass
        else:
            self.good_values.extend([np.True_, np.False_])
        self.bad_values = ['True', 'False']
        self.obj = True

    def test_ast(self):
        # AST for bools changes in various Pythons; ast.Name,
        # ast.NameConstant, ast.Constant. So we ask for whatever this Python
        # version gives.
        expected = ast.parse('True').body[0].value
        result = self.validator.to_ast(True)
        assert result.value == expected.value

    def test_raises_error(self):
        pass  # this one doesn't actually raise an error

    def test_create(self):
        assert self.factory.create('bool') == self.validator

    def test_to_instance(self):
        for inst in [True, False]:
            assert self.validator.to_instance(inst) == inst
