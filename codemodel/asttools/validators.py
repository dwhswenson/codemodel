import ast
import collections

class CodeModelError(Exception):
    pass

class ReturnDictError(CodeModelError):
    pass

### AST VALIDATORS #######################################################

class ScopeTracker(ast.NodeVisitor):
    """NodeVisitor that tracks its current scope.

    Scopes are named using a dot notation, with ``global`` as the outermost
    scope name.
    """
    # inspired by https://stackoverflow.com/a/43166653
    # TODO: currently doesn't handle ``global`` statements
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


class ReturnFinder(ScopeLister):
    """
    Store all the nodes that correspond to a ``return`` statement.
    """
    def visit_Return(self, node):
        self.add_to_scope(node)
        self.generic_visit(node)


def count_returns(tree):
    """Count the number of returns in a tree.
    """
    # NOTE: At one point, we needed single return functions. Improvements to
    # the code made that no longer necessary. Keeping this around because it
    # could be useful, but I don't think codemodel is actually using it
    # anywhere.
    finder = ReturnFinder()
    finder.visit(tree)
    return {scope: len(returns) for scope, returns in finder.values.items()}


def _validate_return_dict_node(node):
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
    finder = ReturnFinder()
    finder.visit(tree)
    nodes = finder[scope]
    for node in nodes:
        if not isinstance(node.value, ast.Dict):
            return False
    return True

def find_required_inputs(tree):
    pass
