import pytest
from unittest import mock

import inspect

import codemodel
from codemodel.code_model import *

class NameMock(object):
    # unittest.mock.Mock has a name attribute, so can't mock it out
    def __init__(self, name):
        self.name = name

class TestCodeModel(object):
    def setup(self):
        from os.path import exists
        foo_param = codemodel.Parameter.from_values(name='foo',
                                                    param_type="Unknown")
        exists_param = codemodel.Parameter(
            parameter=inspect.signature(exists).parameters['path'],
            param_type="Unknown"
        )

        ospath = mock.Mock(import_statement="from os import path",
                           implicit_prefix="path",
                           model_types=['CodeModel'])

        self.packages = {'unpackaged': None, 'packaged': ospath}

        self.models = {
            'unpackaged': CodeModel(name="func", parameters=[foo_param]),
            'packaged': CodeModel(name="exists",
                                  parameters=[exists_param],
                                  package=ospath)
        }

        self.dcts = {
            'unpackaged': {
                'name': 'func',
                'parameters': [{'name': 'foo',
                                'param_type': 'Unknown',
                                'desc': None,
                                'kind': "POSITIONAL_OR_KEYWORD",
                                'default': None,
                                'has_default': False}],
            },
            'packaged': {
                'name': 'exists',
                'parameters': [{'name': 'path',
                                'param_type': 'Unknown',
                                'desc': None,
                                'kind': "POSITIONAL_OR_KEYWORD",
                                'default': None,
                                'has_default': False}],
            }
        }

    @pytest.mark.parametrize("model_name", ["unpackaged", "packaged"])
    def test_to_dict(self, model_name):
        assert self.models[model_name].to_dict() == self.dcts[model_name]

    @pytest.mark.parametrize("model", ["unpackaged", "packaged"])
    def test_from_dict(self, model):
        pkg = self.packages[model]
        result = CodeModel.from_dict(self.dcts[model], package=pkg)
        assert result == self.models[model]

    @pytest.mark.parametrize("model", ["unpackaged", "packaged"])
    def test_dict_serialize_cycle(self, model):
        pkg = self.packages[model]
        serialized = self.models[model].to_dict()
        deserialized = CodeModel.from_dict(serialized, package=pkg)
        assert deserialized == self.models[model]
        reserialized = deserialized.to_dict()
        assert serialized == reserialized

    def test_func_no_package(self):
        with pytest.raises(RuntimeError):
            self.models['unpackaged'].func

    def test_func(self):
        import os.path
        assert self.models['packaged'].func == os.path.exists
