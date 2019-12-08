import ast
import collections
import inspect
import functools

from .validators import *
from .function_handling import func_to_body_tree, get_args_kwargs

### AST REWRITERS ########################################################

def replace_ast_names(ast_tree, ast_param_dict):
    """Replace names in a tree with nodes in a dictionary.

    Parameters
    ----------
    ast_tree : ast.AST
        tree to replace nodes in
    ast_param_dict : Dict[str, ast.AST]
        parameter dictionary mapping parameter name (name ID in the tree) to
        the AST node to replace it with

    Returns
    -------
    ast.AST :
        tree with replaced nodes
    """
    class ReplaceName(ast.NodeTransformer):
        def __init__(self, param_ast_dict):
            super().__init__()
            self.param_ast_dict = param_ast_dict
            #self.node_replacers = {k: node_replacer(v)
            #                       for k, v in param_ast_dict.items()}

        def _is_load_paramdict_node(self, node):
            return (node.id in self.param_ast_dict
                    and isinstance(node.ctx, ast.Load))

        def visit_Name(self, node):
            if self._is_load_paramdict_node(node):
                value = self.param_ast_dict[node.id]
                new_node = self.param_ast_dict[node.id]
                # self.generic_visit(new_node)   # maybe?
                return ast.copy_location(new_node, node)
            return self.generic_visit(node)

    replacer = ReplaceName(ast_param_dict)
    ast_tree = replacer.visit(ast_tree)
    return ast_tree

def return_to_assign(body_tree, assign=None):
    """Convert a return at global (body-tree) scope to an assignment.

    Parameters
    ----------
    body_tree : ast.Module
        the body of the function to convert the return from
    assign : Union[str, None]
        the name to assign the return value to; if None (default) assign to
        the meaningless _
    """
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

    # TODO validate func_tree (what to check?)
    # * `assign` should not be used as a name ID
    # * tree should have explicit return (no implicit return None)
    if assign is None:
        assign = "_"
    replace_returns = ReplaceReturnWithAssign(assign)
    body_tree = replace_returns.visit(body_tree)
    return body_tree

### SPECIFIC COMBOS ######################################################

def global_return_dict_to_assign(body_tree):
    """Replace return of dict at global scope with assignment.

    Converts the dict key to a name in the code, e.g., ``{'foo': bar}``
    because the AST equivalent of ``foo = bar``. This is smart enough not
    to create tautological assignments, such as ``foo = foo``.

    Parameters
    ----------
    body_tree : ast.Module
        AST representation of the body of the function.

    Returns
    -------
    ast.Module :
        AST representation with return dicts replaced by assignment
    """
    class FindGlobalReturns(ScopeLister):
        def visit_Return(self, node):
            self.add_to_scope(node)
            self.generic_visit(node)

    class ReturnDictToAssign(ast.NodeTransformer):
        def __init__(self, replace_nodes):
            super().__init__()
            self.replace_nodes = replace_nodes

        def visit_Return(self, node):
            self.generic_visit(node)
            if node in self.replace_nodes:
                key_names = [key.s for key in node.value.keys]
                assignments = [
                    ast.Assign(targets=[ast.Name(id=key, ctx=ast.Store())],
                               value=value)
                    for key, value in zip(key_names, node.value.values)
                    if not (isinstance(value, ast.Name) and value.id == key)
                ]
                return assignments
            else:
                return node

    # check that we have a valid return dict
    validate_return_dict(body_tree)

    finder = FindGlobalReturns()
    finder.visit(body_tree)
    nodes = finder.values['global']
    dict_nodes = [node for node in nodes
                  if isinstance(node.value, ast.Dict)]
    replacer = ReturnDictToAssign(dict_nodes)
    body_tree = replacer.visit(body_tree)
    return body_tree


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
    tree = func_to_body_tree(func)
    body_tree = global_return_dict_to_assign(tree)
    body_tree = replace_ast_names(body_tree, param_ast_dict)
    return body_tree

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
    tree = func_to_body_tree(func)
    body_tree = return_to_assign(tree, assign)
    body_tree = replace_ast_names(body_tree, param_ast_dict)
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
        funcname = ast.Name(id=func.__name__, ctx=ast.Load())

    func_node = ast.Call(func=funcname, args=ast_args, keywords=ast_kwargs)

    if assign is None:
        root_node = func_node
    else:
        root_node = ast.Assign(
            targets=[ast.Name(id=assign, ctx=ast.Store())],
            value=func_node
        )
    return root_node
