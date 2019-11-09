import pytest
from unittest import mock

import inspect

import codemodel
from codemodel.code_model import *
from codemodel.code_model import _unshadow_property_error

import collections


class SectionsExample(object):
    import ast
    # in the examples, we'll use the input num=3 and the variable name
    # my_counter for the result of the main call
    prepare_data_code = """
    data = []
    for i in range(1, 3 + 1):
        data.extend([i] * i)
    """
    prepare_data_ast = ast.parse(
        "\n".join(line[4:] for line in prepare_data_code.splitlines())
    ).body
    @staticmethod
    def prepare_data(num):
        data = []
        for i in range(1, num + 1):
            data.extend([i] * i)

        return {'data': data}

    make_counter_code = """
    import collections
    my_counter = collections.Counter(data)
    """
    @staticmethod
    def make_counter(data):
        import collections
        return collections.Counter(data)

    @staticmethod
    def pure_ast_make_counter(**params_dict, assign):
        import ast
        return [
            ast.Import(names=[alias(name='collections', asname=None)]),
            ast.Assign(
                targets=[ast.Name(id=assign, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='collections', ctx=ast.Load()),
                        attr='Counter'
                    ),
                    args=[params_dict['data']],
                    keywords=[]
                )
            )
        ]

    after_making_code = """
    my_counter.update([3])
    """
    @staticmethod
    def after_making(counter):
        counter.update([3])
        return {}

    ast_after_making_code = """
    my_counter.update([4])
    """
    @staticmethod
    def pure_ast_after_making(**params_dict):
        import ast
        return [ast.Call(
            func=ast.Attribute(value=ast.Name(id='counter', ctx=ast.Load()),
                               attr='update'),
            args=[ast.List(elts=[ast.Num(4)])]  # gasp! 4 not 3? danger!
        )]


def exists_setup(afile):
    import os
    abspath = os.path.abspath(afile)
    return os.path.exists(abspath)

class NameMock(object):
    # unittest.mock.Mock has a name attribute, so can't mock it out
    def __init__(self, name):
        self.name = name

class TestCodeModel(object):
    def setup(self):
        from os.path import exists
        foo_param = codemodel.Parameter.from_values(name='foo',
                                                    param_type="Unknown")
        self.exists_param = codemodel.Parameter(
            parameter=inspect.signature(exists).parameters['path'],
            param_type="Unknown"
        )
        counter_sig = inspect.signature(collections.Counter)
        counter_params = [codemodel.Parameter(param, "Unknown")
                          for param in counter_sig.parameters.values()]

        ospath = mock.Mock(import_statement="from os import path",
                           implicit_prefix="path",
                           model_types=['CodeModel'])

        self.packages = {'unpackaged': None, 'packaged': ospath}

        self.models = {
            'unpackaged': CodeModel(name="func", parameters=[foo_param]),
            'packaged': CodeModel(name="exists",
                                  parameters=[self.exists_param],
                                  package=ospath),
            'counter': CodeModel(name="Counter", parameters=counter_params),
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

    @pytest.mark.parametrize("pkg, setup, expected", [
        (None, None, None),
        (True, None, True),
        (None, exists_setup, {50: exists_setup}),
        (None, {50: exists_setup}, {50: exists_setup}),
    ])
    def test_set_setup(self, pkg, setup, expected):
        if pkg:
            pkg = self.packages['packaged']
        if expected is True:
            from os.path import exists
            expected = {50: exists}

        model = CodeModel("exists", [self.exists_param], pkg, setup)
        assert model.setup == expected

    def test_set_ast_section_package_default(self):
        # version where we use the packages func
        model = self.models['packaged']
        assert model._ast_funcs == {50: model._default_setup_ast}

    @pytest.mark.parametrize("setup, ast_sections, label", [
        pytest.param(exists_setup, None, "exists_setup", 
                     id="setup-func"),
        pytest.param(
            {10: SectionsExample.prepare_data,
             50: SectionsExample.make_counter,
             70: SectionsExample.after_making},
            None, "sections",
            id="setup-dict"
        ),
        pytest.param(
            {10: SectionsExample.prepare_data,
             50: SectionsExample.make_counter,
             70: SectionsExample.after_making},
            None,  #TODO
            "all_ast",
            id="all-ast"
        ),
        pytest.param(
            {10: SectionsExample.prepare_data,
             50: SectionsExample.make_counter,
             70: SectionsExample.after_making},
            None,  #TODO
            "partial_ast",
            id="partial-ast"
        ),
    ])
    def test_set_ast_sections(self, setup, ast_sections, label):
        sections_param = ...
        name, param = {
            'exists_setup': ("exists_setup", self.exists_param),
            'sections': ("sections_example", sections_param),
            'all_ast': ("sections_example", sections_param),
            'partial_ast': ("sections_example", sections_param)
        }[label]
        model = CodeModel(name, [param], None, setup, ast_sections)

        instantiation_func = codemodel.asttools.instantiation_func_to_ast
        dict_func = codemodel.asttools.return_dict_func_to_ast_body

        try:
            expected = {
                'exists_setup': {50: functools.partial(instantiation_func,
                                                       func=exists_setup)},
                'sections': {
                    10: functools.partial(dict_func,
                                          func=SectionsExample.prepare_data),
                    50: functools.partial(instantiation_func,
                                          func=SectionsExample.make_counter),
                    70: functools.partial(dict_func,
                                          func=SectionsExample.after_making)
                },
            }[label]
        except KeyError:
            pytest.skip()

        assert set(model._ast_funcs.keys()) == set(expected.keys())
        for key, expected_func in expected.items():
            assert model._ast_funcs[key].func == expected_func.func
            assert model._ast_funcs[key].args == expected_func.args
            assert model._ast_funcs[key].keywords == expected_func.keywords


    @pytest.mark.parametrize("setup, expected", [
        (None, (None, None, None)),
        ({50: exists_setup}, ([], exists_setup, [])),
        ({10: SectionsExample.prepare_data,
          50: SectionsExample.make_counter,
          70: SectionsExample.after_making},
         ([SectionsExample.prepare_data], SectionsExample.make_counter,
          [SectionsExample.after_making])),
    ])
    def test_call_func_order(self, setup, expected):
        assert CodeModel._call_func_order(setup) == expected

    @pytest.mark.parametrize("setup", [
        {50: SectionsExample.prepare_data},  # too few
        {50: SectionsExample.make_counter, 60: exists_setup}  # too many
    ])
    def test_call_func_order_error(self, setup):
        with pytest.raises(ValueError):
            CodeModel._call_func_order(setup)

    def test_instantiate(self):
        pytest.skip()

    def test_code_sections(self):
        pytest.skip()


class _UnshadowPropertyExample(object):
    def __init__(self):
        self.has_run = False

    @property
    def bad_property(self):
        raise RuntimeError("Bad!")

    @property
    def self_healing(self):
        if not self.has_run:
            self.has_run = True
            raise RuntimeError("Bad once")
        else:
            return "healed!"

    @property
    def good(self):
        return "fine"

    def other(self):
        pass

@pytest.mark.parametrize("prop", ['bad_property'])
def test_unshadow_property_error_gives_error(prop):
    obj = _UnshadowPropertyExample()
    ErrorType = {'bad_property': RuntimeError}[prop]
    with pytest.raises(ErrorType):
        _unshadow_property_error(obj, prop)

@pytest.mark.parametrize("prop", ['good', 'other', 'does_not_exist'])
def test_unshadow_property_error_gives_result(prop):
    obj = _UnshadowPropertyExample()
    result = {'good': "fine",
              'other': None,
              'does_not_exist': None}[prop]
    assert _unshadow_property_error(obj, prop) == result

def test_unshadow_property_error_self_healing():
    obj = _UnshadowPropertyExample()
    prop = 'self_healing'
    result = 'healed!'
    with pytest.raises(RuntimeError):
        _unshadow_property_error(obj, prop)
    assert _unshadow_property_error(obj, prop) == result

class TestInstance(object):
    def setup(self):
        pass

    def test_getattr(self):
        pytest.skip()

    def test_instance(self):
        pytest.skip()

    def test_code_sections(self):
        pytest.skip()
