import ast
import collections
import inspect

def bind_arguments(func, param_dict):
    sig = inspect.signature(func)
    param_kinds = collections.defaultdict(list)

    for name, param in sig.parameters.items():
        param_kinds[param.kind].append(name)

    def kind_to_list(kind):
        return [param_dict[p] for p in param_kinds[kind]]

    def kind_to_dict(kind):
        return {p: param_dict[p] for p in param_kinds[kind]}

    pos_only = kind_to_list(inspect.Parameter.POSITIONAL_ONLY)
    varpos_list = kind_to_list(inspect.Parameter.VAR_POSITIONAL)
    pos_kw = kind_to_dict(inspect.Parameter.POSITIONAL_OR_KEYWORD)
    kw_only = kind_to_dict(inspect.Parameter.KEYWORD_ONLY)
    varkw_list = kind_to_dict(inspect.Parameter.VAR_KEYWORD)

    # next two checks should never occur
    if len(varpos_list) > 1:  # no-cover
        raise RuntimeError("More than 1 variadic positional argument.")

    if len(varkw_list) > 1:  # no-cover
        raise RuntimeError("More than 1 variadic keyword argument.")

    varpos = varpos_list[0] if varpos_list else []
    varkw = list(varkw_list.values())[0] if varkw_list else {}

    if not varpos:
        bound = sig.bind(*pos_only, **pos_kw, **kw_only, **varkw)
    else:
        bound = sig.bind(*pos_only, *pos_kw.values(), *varpos, **kw_only,
                         **varkw)

    return bound
