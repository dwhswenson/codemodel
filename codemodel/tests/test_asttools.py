import pytest

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
