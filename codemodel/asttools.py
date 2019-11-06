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
    inspect.BoundParameters, which prefers positional arguments).

    Parameters
    ----------
    func : callable
        callable to analyze

    Returns
    -------
    as_pos : list of str
        names of parameters to treat as positional
    var_pos : str
        parameter name for variadic positional arguments (usually ``args``),
        or None if no variadic positional arguments
    as_kw : list of str
        names of parameters to treat as keywords
    var_kw : str
        parameter name for variadic keyword arguments (usually ``kwargs``),
        or None if no variadic keywork arguments
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
    """Get *args and **kwargs appropriate to do func(*args, **kwargs).

    This uses our preference for keywords over positional arguments.

    Parameters
    ----------
    func : callable
    param_dict : dict
        mapping of the string parameter name to the associated value, where
        the parameter name is as given in the func's definition.

    Returns
    -------
    args, kwargs : tuple of list, dict
        appropriate results for func(*args, **kwargs)
    """
    as_pos, var_pos, as_kw, var_kw = organize_parameter_names(func)
    args = [param_dict[p] for p in as_pos]
    if var_pos:
        args += param_dict[var_pos]
    kwargs = {p: param_dict[p] for p in as_kw}
    kwargs.update(param_dict[var_kw])
    inspect.signature(func).bind(*args, **kwargs)  # just to test it
    return args, kwargs


def deindented_source(src):
    """De-indent source if all lines indented.

    This is necessary before parsing with ast.parse to avoid "unexpected
    indent" syntax errors if the function is not module-scope in its
    original implementation (e.g., staticmethods encapsulated in classes).

    Parameters
    ----------
    src : str
        input source

    Returns
    -------
    str :
        de-indented source; the first character of at least one line is
        non-whitespace, and all other lines are deindented by the same
    """
    lines = src.splitlines()
    min_chars_whitespace = float("inf")
    for line in lines:
        if line:
            idx = 0
            # we're Python 3, so we assume you're not mixing tabs and spaces
            while idx < min_chars_whitespace and line[idx] in [" ", '\t']:
                idx += 1

            min_chars_whitespace = min(idx, min_chars_whitespace)

    lines = [line[min_chars_whitespace:] for line in lines]
    src = "\n".join(lines)
    return src


def is_return_dict_function(func):
    """Check whether a function returns a dictionary

    This assumes that the function is single-return.

    Parameters
    ----------
    func : callable
        a single-return functions

    Returns
    bool :
        whether the function returns a dict
    """
    tree = ast.parse(deindented_source(inspect.getsource(func)))
    func_body = tree.body[0].body
    for node in func_body:
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            return True

    return False


def return_dict_func_to_ast_body(func):
    """
    Take a function that returns a dict and prepares it for the body.
    """
    pass

def instantiation_func_to_ast(func):
    """
    """
    pass

def create_call_ast(func, param_dict, assign=None, prefix=None):
    """
    """
    pass
