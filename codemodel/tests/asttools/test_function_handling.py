import pytest

import ast
import astor

from codemodel.asttools.function_handling import *

from .functions_ast import FuncSigHolder


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

@pytest.mark.parametrize("param_dict, results", [
    ({'pkw': 'pkw'}, {}),
    ({'pkw': 'pkw', 'foo': 'foo'}, {'foo': 'foo'})
])
def test_get_unused_params(param_dict, results):
    func = FuncSigHolder.foo_pkw
    assert get_unused_params(func, param_dict) == results


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
