import pytest

import ast
import astor

from codemodel.asttools import *


class FuncSigHolder(object):
    @staticmethod
    def foo_pkw(pkw):
        pass

    def foo_pkw_kw_varkw(pkw, *, kw, **varkw):
        pass

    def foo_pkw_varpos_kw_varkw(pkw, *varpos, kw, **varkw):
        pass

@pytest.mark.parametrize("func, results", [
    (FuncSigHolder.foo_pkw, ([], None, ['pkw'], None)),
    (FuncSigHolder.foo_pkw_kw_varkw, ([], None, ['pkw', 'kw'], 'varkw')),
    (FuncSigHolder.foo_pkw_varpos_kw_varkw, (
        ['pkw'], 'varpos', ['kw'], 'varkw'
    )),
])
def test_organize_parameter_names(func, results):
    assert organize_parameter_names(func) == results


@pytest.mark.parametrize("func, results", [
    (FuncSigHolder.foo_pkw, ([], {'pkw': 'pkw'})),
    (FuncSigHolder.foo_pkw_kw_varkw, ([], {'pkw': 'pkw', 'kw': 'kw',
                                           'var': 'kw'})),
    (FuncSigHolder.foo_pkw_varpos_kw_varkw, (
        ['pkw', 'v', 'a', 'r'], {'kw': 'kw', 'var': 'kw'}
    )),
])
def test_get_args_kwargs(func, results):
    param_dict = {l: l for l in ['p', 'pkw', 'kw']}
    param_dict.update({'varkw': {'var': 'kw'}, 'varpos': ['v', 'a', 'r']})
    assert get_args_kwargs(func, param_dict) == results


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

def test_deindented_source_edge_case():
    src = "\n".join([" ", "    def foo():", "        pass"])
    expected = "\n".join(["", "def foo():", "    pass"])
    assert deindented_source(src) == expected

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

@pytest.mark.parametrize("func, params, expected_code", [
    (
        FuncSigHolder.foo_pkw,
        {'pkw': ast.Str('pkw')},
        "foo_pkw(pkw='pkw')"
    ),
    (
        FuncSigHolder.foo_pkw_varpos_kw_varkw,
        {'pkw': ast.Str('pkw'),
         'varpos': [ast.Str('v'), ast.Str('a'), ast.Str('r')],
         'kw': ast.Str('kw'), 'varkw': {'var': ast.Str('kw')}},
        "foo_pkw_varpos_kw_varkw('pkw', 'v', 'a', 'r', kw='kw', var='kw')"
    ),
])
def test_create_call_ast(func, params, expected_code):
    tree = create_call_ast(func, params)
    assert astor.to_source(tree) == expected_code + '\n'

def test_create_call_ast_assign():
    params = {'pkw': ast.Str('pkw')}
    tree = create_call_ast(FuncSigHolder.foo_pkw, params, assign="foo")
    assert astor.to_source(tree) == "foo = foo_pkw(pkw='pkw')\n"

def test_create_call_ast_prefix():
    params = {'pkw': ast.Str('pkw')}
    tree = create_call_ast(FuncSigHolder.foo_pkw, params, prefix="foo")
    assert astor.to_source(tree) == "foo.foo_pkw(pkw='pkw')\n"


