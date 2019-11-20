import pytest
import collections

from codemodel.generate_json import *

import os   # used in testing

PackageInfo = collections.namedtuple("PackageInfo", "name prefix")

@pytest.mark.parametrize("func, n_params", [(os.path.exists, 1),
                                            (os.path.samefile, 2),
                                            (os.getcwd, 0)])
def test_default_type_desc(func, n_params):
    types, descs = default_type_desc(func)
    assert types == tuple(["Unknown"] * n_params)
    assert descs == tuple([None] * n_params)

def test_codemodel_from_callable():
    pytest.skip()

@pytest.mark.parametrize("import_statement, package_info", [
    ("import os", ("os", "os")),
    # ("import os.path", ("os.path", "os.path")),
    # ("from os import path", ("os.path", "path")),
    # ("import os.path as ospath", (,)),
    # ("from os import path as ospath", (,))
])
def test_package_from_import(import_statement, package_info):
    expected = PackageInfo(*package_info)
    package = package_from_import(import_statement)
    assert package.import_statement == import_statement
    assert package.implicit_prefix == expected.prefic
    assert package.name == expected.name
    assert package.callables == []
    pytest.skip()

def test_make_package():
    pytest.skip()
