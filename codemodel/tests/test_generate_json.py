import pytest
from unittest import mock
import collections
import inspect

from codemodel.generate_json import *
import codemodel

import os   # used in testing

PackageInfo = collections.namedtuple("PackageInfo", "name prefix")
ModelInfo = collections.namedtuple("ModelInfo", "name parameters")

@pytest.mark.parametrize("func, n_params", [(os.path.exists, 1),
                                            (os.path.samefile, 2),
                                            (os.getcwd, 0)])
def test_default_type_desc(func, n_params):
    types, descs = default_type_desc(func)
    assert types == tuple(["Unknown"] * n_params)
    assert descs == tuple([None] * n_params)

@pytest.mark.parametrize("func, model_info", [
    (os.getcwd, ("getcwd", [])),
    (os.path.exists, ("exists", [
        codemodel.Parameter(
            parameter=inspect.Parameter(
                name="path",
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ),
            param_type="Unknown"
        )
    ])),
])
def test_codemodel_from_callable(func, model_info):
    expected = ModelInfo(*model_info)
    model = codemodel_from_callable(func)
    assert model.name == expected.name
    for param, exp_param in zip(model.parameters, expected.parameters):
        assert param == exp_param


def test_codemodel_from_callable_registers():
    package = mock.Mock()
    package.import_statement = "import os.path"
    package.implicit_prefix = "os.path"
    model = codemodel_from_callable(os.path.exists, package=package)
    assert model.name == "exists"
    package.register_codemodel.assert_called_once()


@pytest.mark.parametrize("import_statement, package_info", [
    ("import os", ("os", "os")),
    ("import os.path", ("os.path", "os.path")),
    ("from os import path", ("os.path", "path")),
    ("import os.path as ospath", ("os.path", "ospath")),
    ("from os import path as ospath", ("os.path", "ospath"))
])
def test_package_from_import(import_statement, package_info):
    expected = PackageInfo(*package_info)
    package = package_from_import(import_statement)
    assert package.import_statement == import_statement
    assert package.implicit_prefix == expected.prefix
    assert package.name == expected.name
    assert package.callables == []

@pytest.mark.parametrize("name", [None, "ospath"])
def test_make_package(name):
    import os.path
    package = make_package(
        import_statement="from os import path",
        callable_names=['exists', 'abspath'],
        name=name
    )

    expected_name = {None: "os.path", "ospath": "ospath"}[name]

    assert package.name == expected_name
    assert package.import_statement == "from os import path"
    assert package.implicit_prefix == "path"
    assert len(package.callables) == 2
    assert package.callables[0].name == 'exists'
    assert package.callables[0].func == os.path.exists
