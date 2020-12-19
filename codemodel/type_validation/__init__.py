from .type_validation import (
    CodeModelTypeError, TypeValidation, TypeValidator,
    StandardTypeValidator, STANDARD_TYPES_DICT, ValidatorFactory,
    StandardValidatorFactory, InstanceValidatorFactory, BoolValidator,
)

try:
    import numpy
except ImportError:
    HAS_NUMPY = False
    arr_factory = []
else:
    HAS_NUMPY = True
    from . import array_validation as ndarray
    arr_factory = [ndarray.ArrayValidatorFactory()]

DEFAULT_EXTERNAL_TYPE_FACTORIES = \
        [StandardValidatorFactory(STANDARD_TYPES_DICT)] + arr_factory
