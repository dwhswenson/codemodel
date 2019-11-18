import pytest

import ast
import astor

from codemodel.asttools.rewriters import *
from .functions_ast import FuncSigHolder, ValidateFuncHolder

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

@pytest.mark.parametrize("func, extra_code", [
    (ValidateFuncHolder.valid, ""),
    (ValidateFuncHolder.valid_foo_changed, "foo = 'qux' * 2\n"),
])
def test_return_dict_func_to_ast_body(func, extra_code):
    params = {'foo': ast.Str("qux")}
    tree = return_dict_func_to_ast_body(func, params)
    assert astor.to_source(tree) == "bar = 1\n" + extra_code

@pytest.mark.parametrize("func, assign, extra_code", [
    (ValidateFuncHolder.call_something, "assigned",
     "assigned = baz('qux', bar)"),
    (ValidateFuncHolder.call_something, None, "_ = baz('qux', bar)"),
    (ValidateFuncHolder.no_return, "assigned", "pass"),
    (ValidateFuncHolder.no_return, None, "pass"),
    (ValidateFuncHolder.return_non_dict, "assigned", "assigned = 'qux'"),
    (ValidateFuncHolder.return_non_dict, None, "_ = 'qux'"),

])
def test_instantiation_func_to_ast(func, assign, extra_code):
    params = {'foo': ast.Str("qux")}
    tree = instantiation_func_to_ast(func, params, assign)
    assert astor.to_source(tree) == "bar = 1\n" + extra_code + '\n'
