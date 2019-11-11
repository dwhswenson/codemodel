import re
import pytest
from unittest import mock

import inspect

import codemodel
from codemodel.code_model import *

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
    prepare_data_ast = UserAST(
        ast=ast.parse(
            "\n".join(line[4:] for line in prepare_data_code.splitlines())
        ).body,
        inputs=['num'],
        outputs=['data']
    )

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

    make_counter_ast = UserAST(
        ast=[
            ast.Import(names=[ast.alias(name='collections', asname=None)]),
            ast.Assign(
                targets=[ast.Name(id='counter', ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='collections', ctx=ast.Load()),
                        attr='Counter'
                    ),
                    args=[ast.Name(id='data', ctx=ast.Load())],
                    keywords=[]
                )
            )
        ],
        inputs=['data'],
        outputs=['counter']
    )


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
    after_making_ast = UserAST(
        ast=[ast.Call(
            func=ast.Attribute(value=ast.Name(id='counter', ctx=ast.Load()),
                               attr='update'),
            args=[ast.List(elts=[ast.Num(4)])]  # diff val to verify it
        )],
        inputs=['counter'],
        outputs=[]
    )


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
    ])
    def test_set_ast_sections_with_setup(self, setup, ast_sections, label):
        sections_param = ...  #TODO
        name, param = {
            'exists_setup': ("exists_setup", self.exists_param),
            'sections': ("sections_example", sections_param),
        }[label]
        model = CodeModel(name, [param], None, setup, ast_sections)

        instantiation_func = codemodel.asttools.instantiation_func_to_ast
        dict_func = codemodel.asttools.return_dict_func_to_ast_body

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
            }
        }[label]

        assert set(model._ast_funcs.keys()) == set(expected.keys())
        for key, expected_func in expected.items():
            assert model._ast_funcs[key].func == expected_func.func
            assert model._ast_funcs[key].args == expected_func.args
            assert model._ast_funcs[key].keywords == expected_func.keywords

    def test_set_ast_section_mix_setup_ast(self):
        setup = {10: SectionsExample.prepare_data,
                 50: SectionsExample.make_counter,
                 70: SectionsExample.after_making}
        ast_sections = {70: SectionsExample.after_making_ast}
        param = ... #TODO
        model = CodeModel("mix_setup_ast", [param], None, setup, ast_sections)
        expected_partial = {
            10: functools.partial(asttools.return_dict_func_to_ast_body,
                                  func=setup[10]),
            50: functools.partial(asttools.instantiation_func_to_ast,
                                  func=setup[50])
        }

        for key in [10, 50]:
            # TODO: this may change
            assert model._ast_funcs[key].func == expected_partial[key].func
            assert model._ast_funcs[key].keywords == \
                expected_partial[key].keywords

        assert model._ast_funcs[70] == ast_sections[70]

    def test_set_ast_section_ast(self):
        param = ... #TODO
        setup = {10: SectionsExample.prepare_data,
                 50: SectionsExample.make_counter,
                 70: SectionsExample.after_making}
        ast_sections = {
            10: SectionsExample.prepare_data_ast,
            50: SectionsExample.make_counter_ast,
            70: SectionsExample.after_making_ast}
        model = CodeModel("mix_setup_ast", [param], None, setup, ast_sections)
        assert model._ast_funcs == ast_sections

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

    # instantiate and code_sections are testing in TestInstance

class TestInstance(object):
    def setup(self):
        import os.path
        exists = os.path.exists

        # TODO: try several more complicated code models
        self.models = {
            'os.path.exists': CodeModel(
                name="exists",
                parameters=[codemodel.Parameter(
                    parameter=inspect.signature(exists).parameters['path'],
                    param_type="Unknown"
                )],
                package=mock.Mock(import_statement="from os import path",
                                  implicit_prefix="path",
                                  model_types=['CodeModel'])
            ),
        }
        self.param_dict = {
            'os.path.exists': {'path': __file__},
        }
        self.expected = {
            'os.path.exists': True,
        }
        self.expected_code = {
            'os.path.exists': {
                50: (r"path_exists = path.exists\(path\=\s*'"
                     + str(__file__) + r"'\s*\)")
            },
        }
        self.instances = {
            'os.path.exists': Instance(
                name='path_exists',
                code_model=self.models['os.path.exists'],
                param_dict=self.param_dict['os.path.exists']
            ),
        }

    def test_instance(self):
        model_name = 'os.path.exists'
        model = self.models[model_name]
        instance_obj = self.instances[model_name]
        instance = instance_obj.instance
        assert instance == self.expected[model_name]
        assert instance is instance_obj.instance  # idempotency

    def test_code_name(self):
        model_name = 'os.path.exists'
        instance_obj = self.instances[model_name]
        old_name = instance_obj.name
        assert instance_obj.code_name == instance_obj.name
        instance_obj.code_name = "foo"
        assert instance_obj.code_name != instance_obj.name
        assert instance_obj.name == old_name

    def test_code_sections(self):
        model_name = 'os.path.exists'
        instance_obj = self.instances[model_name]
        code_sections = instance_obj.code_sections
        for sec_id, code in code_sections.items():
            assert re.match(self.expected_code[model_name][sec_id], code)
