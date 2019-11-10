import ast
import collections
import inspect

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
    kwargs = {p: param_dict[p] for p in as_kw}
    if var_kw:
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
    # don't just do func_body[-1] because there might be unreachable
    # statements after the return. First outer-scope return must be reached!
    for node in func_body:
        if isinstance(node, ast.Return):
            return isinstance(node.value, ast.Dict)

    return False

class ReplaceName(ast.NodeTransformer):
    def __init__(self, param_ast_dict):
        super().__init__()
        self.param_ast_dict = param_ast_dict
        #self.node_replacers = {k: node_replacer(v)
        #                       for k, v in param_ast_dict.items()}

    def visit_Name(self, node):
        if node.id in self.param_ast_dict and isinstance(node.ctx, ast.Load):
            value = self.param_ast_dict[node.id]
            new_node = self.param_ast_dict[node.id]
            # self.generic_visit(new_node)   # maybe?
            return ast.copy_location(new_node, node)
        return self.generic_visit(node)

def replace_ast_names(ast_tree, ast_param_dict):
    replacer = ReplaceName(ast_param_dict)
    ast_tree = replacer.visit(ast_tree)
    return ast_tree

def return_dict_func_to_ast_body(func, param_ast_dict):
    """
    Get the body of a return dict function; return replaced with assignment.

    Parameters
    ----------
    func : callable
    param_ast_dict : dict
        mapping of parameter names to AST nodes that can replace them.

    Returns
    -------
    list of ast.AST :
        nodes in the body of the function, ready to be made part of a longer
        function
    """
    tree = ast.parse(deindented_source(inspect.getsource(func)))

    body = []
    for node in tree.body[0].body:
        if isinstance(node, ast.Return):
            break
        body.append(node)

    dict_node = node.value
    #validate(func, tree, dict_node)

    key_names = [key.s for key in node.value.keys]

    assignments = [
        ast.Assign(targets=[ast.Name(key, ctx=ast.Store())], value=value)
        for key, value in zip(key_names, node.value.values)
        if not (isinstance(value, ast.Name) and value.id == key)
    ]
    body.extend(assignments)
    body_tree = ast.Module(body=body)

    body_tree = replace_ast_names(body_tree, param_ast_dict)
    # replace = ReplaceName(param_ast_dict)
    # body_tree = replace.visit(body_tree)

    return body_tree


class ReplaceReturnWithAssign(ast.NodeTransformer):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def visit_Return(self, node):
        new_node = ast.Assign(
            targets=[ast.Name(id=self.name, ctx=ast.Store())],
            value=node.value
        )
        return ast.copy_location(new_node, node)

def instantiation_func_to_ast(func, param_ast_dict, assign=None):
    """Get the body of any functions, converting the returns to assignment.

    Parameters
    ----------
    func : callable
    param_ast_dict : dict
        mapping of parameter names (for func) to ast.AST nodes
    assign : str
        value to assign the return value of the function to

    Returns
    -------
    ast.AST :
        node that represents this statement
    """
    tree = ast.parse(deindented_source(inspect.getsource(func)))
    body_tree = ast.Module(body=tree.body[0].body)
    if assign is None:
        assign = "_"
    # replace_names = ReplaceName(param_ast_dict)
    # body_tree = replace_names.visit(body_tree)
    body_tree = replace_ast_names(body_tree, param_ast_dict)
    replace_returns = ReplaceReturnWithAssign(assign)
    body_tree = replace_returns.visit(body_tree)
    return body_tree

def create_call_ast(func, param_ast_dict, assign=None, prefix=None):
    """Creates a call of the function from scratch.

    Very similar to ``assign = prefix.func(**param_dict)``

    Parameters
    ----------
    func : callable
        the function for the call
    param_dict : dic6
        dictionary of the parameters, maps a string parameter name to the
        AST node that should replace it
    assign : str
        name to assign the result to, or None if no assignment should be
        done
    prefix : str
        package name containing the func or None if not used


    Returns
    -------
    ast.AST :
        node that represents this statement
    """
    ast_args, kwargs = get_args_kwargs(func, param_ast_dict)
    # ast_args = [to_ast(a) for a in args]
    ast_kwargs = [
        ast.keyword(arg=param, value=kwargs[param])
        for param in kwargs
    ]
    if prefix is not None:
        funcname = ast.Attribute(value=ast.Name(id=prefix, ctx=ast.Load()),
                                 attr=func.__name__)
    else:
        funcname = ast.Name(id=func.__name__)

    func_node = ast.Call(func=funcname, args=ast_args, keywords=ast_kwargs)

    if assign is None:
        root_node = func_node
    else:
        root_node = ast.Assign(
            targets=[ast.Name(id=assign, ctx=ast.Store())],
            value=func_node
        )
    return root_node
