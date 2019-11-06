import pytest

import astor

from codemodel.asttools import *


class FuncSigHolder(object):
    def foo_pkw(pkw):
        pass

    def foo_pkw_kw_varkw(pkw, *, kw, **varkw):
        pass

    def foo_pkw_varpos_kw_varkw(pkw, *varpos, kw, **varkw):
        pass

@pytest.mark.parametrize("func", [FuncSigHolder.foo_pkw,
                                  FuncSigHolder.foo_pkw_kw_varkw,
                                  FuncSigHolder.foo_pkw_varpos_kw_varkw])
def test_bind_arguments(func):
    param_dict = {n: n for n in ['p', 'pkw', 'kw']}
    param_dict.update({'varpos': ('v', 'a', 'r', 'p', 'o', 's'),
                       'varkw': {'var': 'kw'}})
    bound = bind_arguments(func, param_dict)
    for (param, value) in bound.arguments.items():
        assert value == param_dict[param]

tab_indented = """
	def indent_test(foo):
		return foo
"""
space_indented = """
    def indent_test(foo):
        return foo
"""
not_indented = """
def indent_test(foo):
    return foo
"""

@pytest.mark.parametrize("src", [tab_indented, space_indented, not_indented])
def test_deindented_source(src):
    deindented = deindented_source(src)
    tree = ast.parse(deindented)
    assert astor.to_source(tree) == not_indented[1:]  # strip leading \n


class ValidateFuncHolder(object):
    def dict_return_global(foo):
        return {'foo': bar}

    def valid(foo):
        return {'foo': foo}

    def no_return(foo):
        pass

    def return_non_dict(foo):
        return foo

@pytest.mark.parametrize("func,expected", [
    (ValidateFuncHolder.dict_return_global, True),
    (ValidateFuncHolder.valid, True),
    (ValidateFuncHolder.no_return, False),
    (ValidateFuncHolder.return_non_dict, False)
])
def test_is_return_dict_function(func, expected):
    assert is_return_dict_function(func) == expected
