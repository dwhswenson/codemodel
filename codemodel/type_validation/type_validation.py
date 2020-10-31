import collections
import numbers
import ast
import codemodel

class CodeModelTypeError(TypeError):
    pass

class TypeValidation(object):
    """Main type validation manager. Typically singleton within an app.

    Parameters
    ----------
    validator_factories
    """
    def __init__(self, validator_factories):
        self.factories = []
        for factory in validator_factories:
            self.register(factory)

        self._validators = {}

    def register(self, factory):
        # TODO: some day we may do something to prevent duplicates; but they
        # can't be used more than once
        self.factories.append(factory)

    def __getitem__(self, type_str):
        try:
            return self._validators[type_str]
        except KeyError:
            for factory in self.factories:
                if factory.is_my_type(type_str):
                    self._validators[type_str] = factory.create(type_str)
                    return self._validators[type_str]

            # if we get here, then we couldn't handle the error
            raise

class TypeValidator(object):
    """
    Parameters
    ----------
    is_my_type : Callable[[str], bool]
        function to determine whether a param_type string should be handler
        by this validator
    to_instance : Callable[[str], Any]
        function to convert a string representation of an instance of this
        type to the instance itself; should raise ValueError is conversion
        fails
    is_valid : Callable[[Any], bool]
        function to validate that the given object is a valid instance of
        this type
    regularized_name : str
        the regularlized name (i.e., without dimensionality) for this type
    """
    def __init__(self, name, regularized_name):
        self.name = name
        self.regularized_name = regularized_name

    def clean_string(self, string_rep):
        return string_rep

    def _to_instance(self, string_rep):
        raise NotImplementedError()

    def to_instance(self, string_rep):
        return self._to_instance(self.clean_string(string_rep))

    def _to_ast(self, string_rep):
        raise NotImplementedError()

    def to_ast(self, string_rep):
        return self._to_ast(self.clean_string(string_rep))

    def is_valid(self, obj):
        raise NotImplementedError()

    def validate(self, obj_str):
        # raise an error is obj isn't a string!
        if not isinstance(obj_str, str):
            raise TypeError("Input to validator should be string version")
        try:
            instance = self.to_instance(obj_str)
        except ValueError:
            return False
        return True


class StandardTypeValidator(TypeValidator):
    def __init__(self, type_str, type_builtin, superclass):
        super().__init__(name=type_str, regularized_name=type_str)
        self.type_builtin = type_builtin
        self.regularized_name = type_str
        self.superclass = superclass

    def _to_instance(self, obj_str):
        return self.type_builtin(obj_str)

    def _to_ast(self, obj_str):
        obj = self.to_instance(obj_str)
        return ast.parse(repr(obj), mode='eval').body

    def is_valid(self, obj):
        return isinstance(obj, self.superclass)


# def type_str_is_my_type(my_type_str):
    # def is_my_type(type_str):
        # return type_str == my_type_str
    # return is_my_type

# def isinstance_is_valid(superclass):
    # def is_valid(obj):
        # return isinstance(obj, superclass)
    # return is_valid

# TODO: move these to a separate file
STANDARD_TYPES_DICT = {
    # maps string to (builtin_func, superclass)
    'int': (int, numbers.Integral),
    'float': (float, numbers.Real),
    'str': (str, str),
}

ValidatorFactory = collections.namedtuple(
    "ValidatorFactory", "is_my_type create"
)

class StandardValidatorFactory(object):
    ValidatorClass = StandardTypeValidator
    def __init__(self, types_dict):
        self.types_dict = types_dict

    def is_my_type(self, type_str):
        return type_str in self.types_dict

    def create(self, type_str):
        type_builtin, superclass = self.types_dict[type_str]
        return self.ValidatorClass(type_str, type_builtin, superclass)


class BoolValidator(object):
    """Validator for true booleans (where input is True/False, not string).

    Mix-in the factory functionality here, too.
    """
    def __init__(self):
        self.name = 'bool'
        self.regularized_name = 'bool'

    def to_instance(self, input_val):
        return input_val

    def to_ast(self, input_val):
        return ast.NameConstant(input_val)

    def is_valid(self, obj):
        # do this in case we get a np.True/False
        return obj == True or obj == False

    def validate(self, obj):
        return self.is_valid(obj)

    def is_my_type(self, type_str):
        return type_str == 'bool'

    def create(self, type_str):
        return self


class InstanceTypeValidator(StandardTypeValidator):
    def validate(self, obj_str):
        return isinstance(obj_str, codemodel.Instance)

    def _to_ast(self, obj_str):
        return ast.Name(id=obj_str.code_name, ctx=ast.Load())

class InstanceValidatorFactory(StandardValidatorFactory):
    ValidatorClass = InstanceTypeValidator
    def __init__(self):
        super().__init__(types_dict={
            'instance': (lambda x: x.instance, codemodel.Instance)
        })
