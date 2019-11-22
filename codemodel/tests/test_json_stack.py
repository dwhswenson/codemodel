import pytest
import inspect
import json
import tempfile

from codemodel.json_stack import *

def func(pkw, *, kw='foo', kw2=None):
    # empty function; signature used in testing
    pass


class TestParameter(object):
    def setup(self):
        self.sig_parameters = inspect.signature(func).parameters
        self.params = {p.name: Parameter(p, "Unknown")
                       for p in self.sig_parameters.values()}
        # create a set of relevant parameters
        self.dcts = {
            'pkw': {'name': 'pkw',
                    'param_type': "Unknown",
                    'kind': "POSITIONAL_OR_KEYWORD",
                    'has_default': False,
                    'default': None,
                    'desc': None},
            'kw': {'name': 'kw',
                   'param_type': "Unknown",
                   'kind': "KEYWORD_ONLY",
                   'has_default': True,
                   'default': 'foo',
                   'desc': None},
            'kw2': {'name': 'kw2',
                    'param_type': "Unknown",
                    'kind': "KEYWORD_ONLY",
                    'has_default': True,
                    'default': None,
                    'desc': None},
        }
        pass

    def test_from_values(self):
        param = Parameter.from_values(
            name="pkw",
            param_type="Unknown"
        )
        assert param == self.params['pkw']

    def test_name(self):
        assert self.params['pkw'].name == 'pkw'

    @pytest.mark.parametrize("name", ['pkw', 'kw', 'kw2'])
    def test_default(self, name):
        assert self.params[name].default == self.dcts[name]['default']

    @pytest.mark.parametrize("name", ['pkw', 'kw', 'kw2'])
    def test_has_default(self, name):
        assert self.params[name].has_default == self.dcts[name]['has_default']


    @pytest.mark.parametrize("name", ['pkw', 'kw', 'kw2'])
    def test_to_dict(self, name):
        assert self.params[name].to_dict() == self.dcts[name]

    @pytest.mark.parametrize("name", ['pkw', 'kw', 'kw2'])
    def test_from_dict(self, name):
        assert Parameter.from_dict(self.dcts[name]) == self.params[name]

    @pytest.mark.parametrize("name", ['pkw', 'kw', 'kw2'])
    def test_dict_serialize_cycle(self, name):
        serialized = self.params[name].to_dict()
        deserialized = Parameter.from_dict(serialized)
        assert deserialized == self.params[name]
        reserialized = deserialized.to_dict()
        assert serialized == reserialized


class TestPackage(object):
    def setup(self):
        from os.path import exists
        callables = [codemodel.CodeModel(
            name="exists",
            parameters=[Parameter(
                inspect.signature(exists).parameters['path'],
                param_type="Unknown"
            )]
        )]
        self.package = Package(name="ospath",
                               callables=callables,
                               import_statement="from os import path",
                               implicit_prefix="path")

        self.dct = {
            'name': 'ospath',
            'import_statement': "from os import path",
            'implicit_prefix': "path",
            'model_types': ['CodeModel'],
            'callables': [{
                'name': 'exists',
                'parameters': [{'name': 'path',
                                'param_type': 'Unknown',
                                'desc': None,
                                'kind': "POSITIONAL_OR_KEYWORD",
                                'default': None,
                                'has_default': False}],
            }]
        }

    def test_to_dict(self):
        assert self.package.to_dict() == self.dct

    def test_from_dict(self):
        assert Package.from_dict(self.dct) == self.package

    def test_module(self):
        import os.path
        assert self.package.module == os.path

    def test_dict_serialize_cycle(self):
        serialized = self.package.to_dict()
        deserialized = Package.from_dict(serialized)
        assert deserialized == self.package
        reserialized = deserialized.to_dict()
        assert serialized == reserialized

    def test_load_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode='w+') as tmp:
            json.dump([self.package.to_dict()], tmp)
            tmp.flush()
            loaded = load_json(tmp.name)
            assert len(loaded) == 1
            assert loaded[0] == self.package
