import ast
import collections
import inspect

def bind_arguments(func, param_dict):
    # TODO: remove; replace by below
    """Create inspect.BoundArguments based on func and param_dict

    Parameters
    ----------
    func : callable
    param_dict : dict

    Returns
    -------
    inspect.BoundArguments
    """
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


def organize_parameter_names(func):
    """Organize the parameter names by how they will be displayed.

    This prefers to use keywords whenever possible (compared to
    inspect.BoundParameters, which seems to prefer positional arguments).
    """
    sig = inspect.signature(func)
    param_kinds = collections.defaultdict(list)

    for name, param in sig.parameters.items():
        param_kinds[param.kind].append(name)

    as_pos = []
    var_pos = None
    as_kw = []
    var_kw = {}

    as_pos += param_kinds[inspect.Parameter.POSITIONAL_ONLY]

    if inspect.Parameter.VAR_POSITIONAL in param_kinds:
        if len(param_kinds[inspect.Parameter.VAR_POSITIONAL]) > 1:  # no-cover
            raise RuntimeError("More than 1 variadic positional argument.")
        var_pos = param_kinds[inspect.Parameter.VAR_POSITIONAL][0]
        as_pos += param_kinds[inspect.Parameter.POSITIONAL_OR_KEYWORD]
    else:
        as_kw += param_kinds[inspect.Parameter.POSITIONAL_OR_KEYWORD]

    as_kw += param_kinds[inspect.Parameter.KEYWORD_ONLY]

    if inspect.Parameter.VAR_KEYWORD in param_kinds:
        if len(param_kinds[inspect.Parameter.VAR_KEYWORD]) > 1:  # no-cover
            raise RuntimeError("More than 1 variadic keyword argument.")
        var_kw = param_kinds[inspect.Parameter.VAR_KEYWORD][0]

    return as_pos, var_pos, as_kw, var_kw

def get_args_kwargs(func, param_dict):
    as_pos, var_pos, as_kw, var_kw = organize_parameter_names(func)
    args = [param_dict[p] for p in as_pos]
    if var_pos:
        args += param_dict[var_pos]
    kwargs = {p: param_dict[p] for p in as_kw}
    kwargs.update(param_dict[var_kw])
    inspect.signature(func).bind(*args, **kwargs)  # just to test it
    return args, kwargs


def default_call_ast(func, param_dict, prefix=None, assign=None):
    sig = inspect.signature(func)
    args = []
    kwargs = []

    pass
