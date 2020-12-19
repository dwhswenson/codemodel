import ast
import inspect
import collections

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
    # TODO: this part can depend get the parameters list from either func
    # signature (as now) or from CodeModel.parameters ... enables a lot of
    # this to be done without the package installed
    sig = inspect.signature(func)
    parameters = sig.parameters

    param_kinds = collections.defaultdict(list)
    for name, param in parameters.items():
        param_kinds[param.kind].append(name)

    as_pos = []
    var_pos = None
    as_kw = []
    var_kw = None

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

    This uses our preference for keywords over positional arguments. Note
    that the input ``param_dict`` can contain extra parameters that are
    *not* used in the callable.

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
    kwargs = {}
    for p in as_kw:
        try:
            param = param_dict[p]
        except KeyError:
            pass  # use default -- TODO: check that there is one?
        else:
            kwargs.update({p: param})
    if var_kw:
        kwargs.update(param_dict[var_kw])
    inspect.signature(func).bind(*args, **kwargs)  # just to test it
    return args, kwargs

def get_unused_params(func, param_dict):
    """Return parameters in the param_dict that aren't inputs to func

    Parameters
    ----------
    func : Callable[[Any], Any]
    param_dict : Dict[str, Any]
        mapping of the string parameter name to the associated value, where
        the parameter name is as given in the func's definition.

    Returns
    -------
    Dict[str, Any] :
        parameters that aren't inputs to func
    """
    func_params = {p for p in inspect.signature(func).parameters}
    unused = set(param_dict.keys()) - func_params
    return {k: param_dict[k] for k in unused}

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
    n_chars = float("inf")
    for line in lines:
        len_line = len(line)
        idx = 0

        # we're Python 3, so we assume you're not mixing tabs and spaces
        while idx < n_chars and idx < len_line and line[idx] in [" ", '\t']:
            idx += 1

        if len_line > idx:
            n_chars = min(idx, n_chars)

    lines = [line[n_chars:] for line in lines]
    src = "\n".join(lines)
    return src

def func_to_body_tree(func):
    src = deindented_source(inspect.getsource(func))
    func_tree = ast.parse(src)
    body_tree = ast.Module(func_tree.body[0].body)
    return body_tree
