import ast

def validate_imports(imports):
    """Validate that the given list of imports only includes imports.

    Parameters
    ----------
    imports : list of str
        string that should be import statements
    """
    if isinstance(imports, str):
        imports = [imports]
    for line in imports:
        tree = ast.parse(line)
        if not isinstance(tree.body[0], (ast.Import, ast.ImportFrom)):
            raise RuntimeError("Non-import statement in imports: "
                               + str(line))


def _name_or_asname(alias):
    """Take alias node from AST and return the name bound to import"""
    return alias.asname if alias.asname else alias.name


class _FindImportNames(ast.NodeVisitor):
    # identify all the import names, map them to canonical names
    def __init__(self):
        super().__init__()
        self.import_names = {}

    def visit_ImportFrom(self, node):
        dct = {_name_or_asname(alias): node.module + '.' + alias.name
               for alias in node.names}
        self.import_names.update(dct)
        self.generic_visit(node)

    def visit_Import(self, node):
        dct = {_name_or_asname(alias): alias.name for alias in node.names}
        self.import_names.update(dct)
        self.generic_visit(node)


def import_names(imports):
    """Link import names to modules for import lines of code.

    Note that this doesn't handle * imports, e.g., ``from foo import *``.

    Parameters
    ----------
    imports : list of str
        lines of code representing imports

    Returns
    -------
    dict :
        mapping of name (used in source) to an importable name of the module
    """
    if isinstance(imports, str):
        imports = [imports]
    validate_imports(imports)
    tree = ast.parse("\n".join(imports))
    finder = _FindImportNames()
    finder.visit(tree)
    return finder.import_names
