import ast
import collections
import functools


class CodeModelError(Exception):
    pass


class ReturnDictError(CodeModelError):
    pass


class ScopeTracker(ast.NodeVisitor):
    """NodeVisitor that tracks its current scope.

    Scopes are named using a dot notation, with ``global`` as the outermost
    scope name.
    """
    # inspired by https://stackoverflow.com/a/43166653
    # TODO: currently doesn't handle ``global`` statements
    # TODO: I think this also needs to handle comprehensions -- aren't those
    # scope-defining?
    # NOTE: this will not handle cases where you redefine a scope (e.g., def
    # a function, use it, then def another function with the same name).
    # If you do that, you are evil and should be in jail, so I don't care if
    # your code doesn't work here.
    def __init__(self):
        self.context = []
        self._register_context('global')

    @property
    def current_context(self):
        return ".".join(self.context)

    def _register_context(self, name):
        self.context.append(name)

    def _stack_visit(self, node, name=None):
        if name is None:
            name = node.name

        self._register_context(name)
        self.generic_visit(node)
        self.context.pop()

    def visit_FunctionDef(self, node):
        self._stack_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._stack_visit(node)

    def visit_Lambda(self, node):
        self._stack_visit(node, name='lambda')


class ScopeLister(ScopeTracker):
    """
    Abstract scope tracker to adds items to a per-scope list when triggered.

    The list of items for each scope can be obtained using the ``getitem``
    syntax with the scope name. For example, ``lister[scope]``.
    """
    def __init__(self):
        self.values = collections.defaultdict(list)
        super().__init__()

    def _register_context(self, name):
        super()._register_context(name)
        self.values[self.current_context] = []

    def add_to_scope(self, obj):
        self.values[self.current_context].append(obj)

    def __getitem__(self, scope):
        if scope not in self.values:
            # TODO: change this up so we know which scopes exist and are
            # empty vs which ones do not exist
            raise CodeModelError("No values for scope: " + str(scope))
        return self.values[scope]


def collect_all_names(tree):
    """Collect all names within an AST.

    Parameters
    ----------
    tree : ast.AST
        the AST to search

    Returns
    -------
    List[str] :
        list of names in the tree
    """
    class NameCollector(ast.NodeVisitor):
        def __init__(self):
            super().__init__()
            self.names = set([])

        def visit_Name(self, node):
            self.names.update([node.id])
            self.generic_visit(node)

    visitor = NameCollector()
    visitor.visit(tree)
    return visitor.names


class AssignmentsTracker(ScopeTracker):
    """Scope-based tracking of names that receive assignments."""
    def __init__(self):
        self.assignments = {}
        super().__init__()

    def _register_context(self, name):
        super()._register_context(name)
        self.assignments[self.current_context] = set([])

    def _check_target(self, target):
        names = collect_all_names(target)
        self.assignments[self.current_context].update(names)

    def visit_Assign(self, node):
        for target in node.targets:
            self._check_target(target)

        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self._check_target(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._check_target(node.target)
        self.generic_visit(node)


class NameLoadTracker(ScopeTracker):
    """Identify names that are not defined in each scope."""
    def __init__(self):
        self.known = {}
        self.required_inputs = {}
        self.gets_assigned = {}
        # unknown and special are to left around for debug stuff
        self._unknown = []
        self._special = []
        super().__init__()

    def _register_context(self, name):
        super()._register_context(name)
        self.known[self.current_context] = set([])
        self.required_inputs[self.current_context] = set([])
        self.gets_assigned[self.current_context] = set([])

    def visit_AugAssign(self, node):
        # AugAssign gives ctx=ast.Store, but also requires loading
        known = self.known[self.current_context]
        required = self.required_inputs[self.current_context]

        if isinstance(node.target, ast.Name) and node.target.id not in known:
            required.update([node.target.id])
            self._special.append(node.target)

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # add func name to known in prev scope, args to known in new scope
        # completely overrides the _stack_visit process
        self.known[self.current_context].update([node.name])
        self._register_context(node.name)
        arg_node = node.args
        args = [a.arg for a in arg_node.args + arg_node.kwonlyargs]
        for var in [arg_node.vararg, arg_node.kwarg]:
            if var is not None:
                args.append(var.arg)

        self.known[self.current_context].update(args)
        self.generic_visit(node)
        self.context.pop()

    def visit_Name(self, node):
        known = self.known[self.current_context]
        required = self.required_inputs[self.current_context]
        if isinstance(node.ctx, ast.Load) and node.id not in known:
            required.update([node.id])
        elif isinstance(node.ctx, ast.Store):
            known.update([node.id])
        else:
            self._unknown.append(node)
        self.generic_visit(node)


def find_undefined_names(tree):
    """Identify all names that are not defined in-scope for an AST.

    Parameters
    ----------
    tree : ast.AST
        the AST to search

    Returns
    -------
    List[str] :
        list of names that are not defined in-scope
    """
    walker = NameLoadTracker()
    walker.visit(tree)
    contexts = list(walker.known.keys())
    parent_contexts = {
        context: [ctx for ctx in contexts
                  if context.startswith(ctx) and ctx != context]
        for context in contexts
    }
    required = {}
    for context, parents in parent_contexts.items():
        known_by_context = [walker.known[ctx] for ctx in parents]
        if known_by_context:
            all_known = functools.reduce(lambda a,b: a | b, known_by_context)
        required[context] = [var for var in walker.required_inputs[context]
                             if var not in all_known]

    return sum(required.values(), [])


class ReturnFinder(ScopeLister):
    """Store all the nodes that correspond to a ``return`` statement."""
    def visit_Return(self, node):
        self.add_to_scope(node)
        self.generic_visit(node)


def count_returns(tree):
    """Count the number of returns in a tree, per scope

    Parameters
    ----------
    tree : ast.AST
        the tree to search

    Returns
    -------
    Dict[str, int] :
        mapping of scope to count of returns in that scope
    """
    # NOTE: At one point, we needed single return functions. Improvements to
    # the code made that no longer necessary. Keeping this around because it
    # could be useful, but I don't think codemodel is actually using it
    # anywhere.
    finder = ReturnFinder()
    finder.visit(tree)
    return {scope: len(returns) for scope, returns in finder.values.items()}


def _validate_return_dict_node(node):
    """Ensure that a particular node is a return dict.

    Checks that there are no non-dict return functions and that the return
    dict keys are all strings.
    """
    if not isinstance(node.value, ast.Dict):
        raise ReturnDictError("Non-dict return value found in function.")

    for key in node.value.keys:
        if not isinstance(key, ast.Str):
            raise ReturnDictError("Return dictionary key not a string")

    return True


def validate_return_dict(tree, scope='global'):
    """Check that the tree at the desired scope is a return dict function

    A valid return dict function must:
    * only return dictionaries
    * all return dictionary keys must be strings
    * all return dictionaries must have the same keys

    This raises a ReturnDictError if any of those conditions are not true.

    Parameters
    ----------
    tree : ast.AST
        the tree to search
    scope : str
        the scrope to check as a return dict

    Returns
    -------
    bool :
        True if valid return dict func; raises error if not
    """
    finder = ReturnFinder()
    finder.visit(tree)
    nodes = finder[scope]
    if len(nodes) == 0:
        raise ReturnDictError("No returns found in function.")
    keys = None
    for node in nodes:
        _validate_return_dict_node(node)
        local_keys = set(key.s for key in node.value.keys)

        if keys is None:
            keys = local_keys

        if keys != local_keys:
            raise ReturnDictError("Return dicts have different keys!")
    return True


def is_return_dict_func(tree, scope='global'):
    """Check whether the tree is the body of a return dict functions.

    Parameters
    ----------
    tree : ast.AST
        the tree to search
    scope : str
        the scrope to check as a return dict

    Returns
    -------
    bool :
        whether this is a return dict
    """
    finder = ReturnFinder()
    finder.visit(tree)
    nodes = finder[scope]
    for node in nodes:
        if not isinstance(node.value, ast.Dict):
            return False
    return True
