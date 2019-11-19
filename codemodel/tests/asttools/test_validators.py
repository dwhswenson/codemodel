import pytest

import ast
import inspect
import astor

from codemodel.asttools.function_handling import deindented_source
from codemodel.asttools.validators import *
from .functions_ast import (
    nested_scopes, return_dict_tester, undefined_names_tester
)

@pytest.mark.parametrize("func, counts", [
    (nested_scopes, {'global': 0,
                     'global.nested_scopes': 3,
                     'global.nested_scopes.bar': 2,
                     'global.nested_scopes.Baz': 0,
                     'global.nested_scopes.Baz.__init__': 0,
                     'global.nested_scopes.Baz.qux': 1}),
    (return_dict_tester, {'global': 0,
                          'global.return_dict_tester': 3,
                          'global.return_dict_tester.inner': 2}),
])
def test_count_returns(func, counts):
    tree = ast.parse(inspect.getsource(func))
    assert count_returns(tree) == counts


def test_validate_return_dict():
    tree = ast.parse(inspect.getsource(return_dict_tester))
    assert validate_return_dict(tree, 'global.return_dict_tester')


def test_validate_return_dict_bad_scope():
    tree = ast.parse(inspect.getsource(return_dict_tester))
    with pytest.raises(CodeModelError):
        validate_return_dict(tree, 'foo')


def test_validate_return_dict_non_dict():
    tree = ast.parse(inspect.getsource(nested_scopes))
    with pytest.raises(ReturnDictError):
        validate_return_dict(tree, 'global.nested_scopes')

    tree = ast.parse(inspect.getsource(return_dict_tester))
    with pytest.raises(ReturnDictError):
        validate_return_dict(tree, 'global')


def test_validate_return_dict_diff_keys():
    tree = ast.parse(inspect.getsource(return_dict_tester))
    with pytest.raises(ReturnDictError):
        validate_return_dict(tree, 'global.return_dict_tester.inner')


@pytest.mark.parametrize("tree, expected", [
    (ast.parse(inspect.getsource(undefined_names_tester)), ['blue']),
])
def test_find_undefined_names(tree, expected):
    assert find_undefined_names(tree) == expected


def test_NameLoadTracker_args_kwargs():
    def foo(*args, **kwargs):
        pass

    tree = ast.parse(deindented_source(inspect.getsource(foo)))
    walker = NameLoadTracker()
    walker.visit(tree)
    assert 'args' in walker.known['global.foo']
    assert 'kwargs' in walker.known['global.foo']


def test_AssignmentsTracker():
    tree = ast.parse(inspect.getsource(undefined_names_tester))
    tracker = AssignmentsTracker()
    tracker.visit(tree)
    assert tracker.assignments == {
        'global': set([]),
        'global.undefined_names_tester': {'alpha', 'beta', 'a', 'b'},
        'global.undefined_names_tester.bar': {'baz'}
    }
