import ast
import collections

class CodeModelError(Exception):
    pass

class ReturnDictError(CodeModelError):
    pass

### AST VALIDATORS #######################################################

class ScopeTracker(ast.NodeVisitor):
    # inspired by https://stackoverflow.com/a/43166653
    # TODO: currently doesn't handle ``global`` statements
    # NOTE: this will not handle cases where you redefine a scope (e.g., def
    # a function, use it, then def another function with the same name).
    # If you do that, you are evil and should be in jail, so I don't care if
    # your code doesn't work here.
    def __init__(self):
        self.context = ['global']

    def _stack_visit(self, node, name=None):
        if name is None:
            name = node.name

        self.context.append(name)
        self.generic_visit(node)
        self.context.pop()

    def visit_FunctionDef(self, node):
        self._stack_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._stack_visit(node)

    def visit_Lambda(self, node):
        self._stack_visit(node, name='lambda')


class ScopeCounter(ScopeTracker):
    def __init__(self):
        super().__init__()
        self.count = collections.defaultdict(int)

    def add_to_scope(self, count=1):
        self.count[".".join(self.context)] += count


class ScopeLister(ScopeTracker):
    def __init__(self):
        super().__init__()
        self.values = collections.defaultdict(list)

    def add_to_scope(self, obj):
        self.values[".".join(self.context)].append(obj)

class ReturnFinder(ScopeLister):
    def visit_Return(self, node):
        self.add_to_scope(node)
        self.generic_visit(node)


def count_returns(tree):
    """
    """
    finder = ReturnFinder()
    finder.visit(tree)
    return {scope: len(returns) for scope, returns in finder.values.items()}

def validate_return_dict(tree, scope='global'):
    finder = ReturnFinder()
    finder.visit(tree)
    nodes = finder.values[scope]
    keys = None
    for node in nodes:
        if not isinstance(node.value, ast.Dict):
            raise ReturnDictError("Non-dict return value found in function.")
        local_keys = set(key.s for key in node.values.keys)
        if keys is None:
            keys = local_keys
        if keys != local_keys:
            raise ReturnDictError("Return dicts have different keys!")
    return True

def is_return_dict_func(tree, scope='global'):
    finder = ReturnFinder()
    finder.visit(tree)
    nodes = finder.values[scope]
    for node in nodes:
        if not isinstance(node.value, ast.Dict):
            return False
    return True

def find_required_inputs(tree):
    pass



