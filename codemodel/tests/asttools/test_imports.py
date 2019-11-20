import pytest

from codemodel.asttools.imports import *

# used in multiple parametrized tests
IMPORT_NAMES = {
    "import sys": ('sys', 'sys'),
    "import os.path": ("os.path", "os.path"),
    "from os import path": ("path", "os.path"),
    "import sys as foo": ("foo", "sys"),
    "from sys import *": None
}

@pytest.mark.parametrize("imp", list(IMPORT_NAMES.keys()))
def test_validate_imports(imp):
    validate_imports(imp)

def test_validate_imports_multiple():
    imports = ["import sys", "import foo"]
    validate_imports(imports)

def test_validate_imports_fails():
    imports = ["import sys", "import foo", "foo.bar()"]
    with pytest.raises(RuntimeError):
        validate_imports(imports)

@pytest.mark.parametrize("imp,name", [
    (imp, name) for imp, name in IMPORT_NAMES.items() if name is not None
])
def test_import_names(imp, name):
    code_name, canonical_name = name
    imp_names = import_names(imp)
    assert len(imp_names) == 1
    assert imp_names[code_name] == canonical_name
