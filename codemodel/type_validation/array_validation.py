from .type_validation import \
        TypeValidator, ValidatorFactory, CodeModelTypeError

import ast
import astor

import numpy as np

def parse_array_type(type_str):
    """
    Parameters
    ----------
    type_str : str
        string matching "array(SHAPE, DTYPE)" where SHAPE is either an int
        or a tuple of ints/Ellipsis and DTYPE is a valid numpy dtype
    """
    # this is such a dirty trick to get shape and dtype.... but ast is
    # stdlib, and besides, it's used a lot in this project anyway. And this
    # doesn't take much code.
    def num_or_ellipsis(item):
        if isinstance(item, ast.Num):
            return item.n
        elif isinstance(item, ast.Ellipsis):
            return ...
        else:
            raise RuntimeError("This will be caught, message never seen")

    try:
        tree = ast.parse(type_str)
        if tree.body[0].value.func.id != 'array':
            raise RuntimeError("Bad func name... this will never be seen.")
        shape_ast, dtype_ast = tree.body[0].value.args
        dtype = np.dtype(dtype_ast.id)
        if isinstance(shape_ast, ast.Num):
            shape_ast_elts = [shape_ast]
        else:
            shape_ast_elts = shape_ast.elts

        shape = tuple(num_or_ellipsis(e) for e in shape_ast_elts)
    except:
        # if anything above went wrong, we had a problem parsing the
        # type_str -- so it doesn't matter that we have a big try block, and
        # it doesn't matter that we catch any error. We raise our own.
        raise CodeModelTypeError("Unable to interpret array-like type: ",
                                 type_str)

    return shape, dtype


def is_array_type(type_str):
    try:
        shape, dtype = parse_array_type(type_str)
    except CodeModelTypeError:
        return False
    return shape is not None and dtype is not None


class ArrayTypeValidator(TypeValidator):
    """
    Parameter
    ---------
    type_str : str
        string specifying this type. For arrays, these must be of the format
        ``array(shape, dtype)``, where shape is a tuple of ints (or a single
        int, which is interpreted as a length-1 tuple) and dtype is a string
    """
    def __init__(self, type_str):
        # TODO: add string cleaning
        super().__init__(name=type_str, regularized_name="array")
        self.shape, self.dtype = parse_array_type(type_str)

    def _to_instance(self, obj_str):
        try:
            arr = ast.literal_eval(obj_str)
            obj = np.array(arr, dtype=self.dtype)
            if not self.is_valid(obj):
                raise ValueError("Invalid array: check shape and dtype.")
        except:
            # if it didn't work for any reason, we raise our own ValueError
            raise ValueError("Unable to make np.array(" + obj_str + ", "
                             + "dtype=" + str(self.dtype))
        return obj

    def _to_ast(self, obj_str):
        input_ast = ast.parse(obj_str, filename="<user>", mode="eval")
        tree = ast.Call(
            func=ast.Attribute(value=ast.Name(id='np'), attr='array'),
            args=[input_ast.body],
            keywords=[ast.keyword(arg='dtype',
                                  value=ast.Str(str(self.dtype)))]
        )
        return tree

    def is_valid(self, obj):
        asarray = np.asarray(obj)  # this may need a try/except

        if asarray.dtype != self.dtype:
            return False

        arr_shape = asarray.shape
        if len(arr_shape) != len(self.shape):
            return False

        for arr_dim, expected in zip(arr_shape, self.shape):
            if arr_dim != expected and expected != Ellipsis:
                return False

        # if we can't find a reason it isn't valid, then it is valid!
        return True

# TODO: in the future, we can add string cleaning functions to justify this
# as a class (give it a need for an __init__)
class ArrayValidatorFactory(object):
    def is_my_type(self, type_str):
        return is_array_type(type_str)

    def create(self, type_str):
        return ArrayTypeValidator(type_str)
