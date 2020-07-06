import pytest
import functools
import random
from unittest.mock import MagicMock, patch

import codemodel
from codemodel.script_model import *

@pytest.mark.parametrize("case", ["single", "multiple", "none"])
def test_get_instance_dependencies(case):
    foo = MagicMock(spec=codemodel.Instance, param_dict={'foo_a': 10})
    bar = MagicMock(spec=codemodel.Instance, param_dict={'bar_a': 10})
    param_dict = {
        "single": {'my_foo': foo},
        "multiple": {'my_foo': foo, 'my_bar': bar},
        "none": {'my_foo': 10},
    }[case]
    expected = {
        'single': [foo],
        'multiple': [foo, bar],
        'none': [],
    }[case]
    inst = MagicMock(spec=codemodel.Instance, param_dict=param_dict)
    deps = get_instance_dependencies(inst)
    assert deps == expected

def _code_model_alpha(list_of_objs, is_reversed=False):
    ordered = list(sorted(list_of_objs,
                          key=lambda x: str(x.code_model.name)))
    return ordered

class TestScriptModel(object):
    def setup(self):
        foo = MagicMock(dependencies=[],
                        code_model=MagicMock(package=None, name='a'),
                        code_sections={50: 'foo_50'})
        bar = MagicMock(dependencies=[foo],
                        code_model=MagicMock(package=None, name='b'),
                        code_sections={10: 'bar_10', 50: 'bar_50',
                                       90: 'bar_90'})
        baz = MagicMock(dependencies=[foo],
                        code_model=MagicMock(package=None, name='c'),
                        code_sections={10: 'baz_10', 50: 'baz_50'})

        self.instances = [foo, bar, baz]
        self.script_model = ScriptModel()
        for instance in self.instances:
            self.script_model.register_instance(instance)

        self.instance_order = {foo: 0, bar: 1, baz: 2}
        self.ordered_blocks = [
            Block(10, bar, 'bar_10'), Block(10, baz, 'baz_10'),
            Block(50, foo, 'foo_50'), Block(50, bar, 'bar_50'),
            Block(50, baz, 'baz_50'), Block(90, bar, 'bar_90')
        ]

    def _make_model(self, is_reversed):
        callback = functools.partial(_code_model_alpha,
                                     is_reversed=is_reversed)
        script_model = ScriptModel(order_callback=callback)
        for inst in self.instances:
            script_model.register_instance(inst)
        return script_model

    def test_register_instance(self):
        script_model = ScriptModel()
        assert script_model.instances == []
        script_model.register_instance(self.instances[0])
        assert script_model.instances == [self.instances[0]]

    def test_make_blocks(self):
        blocks = self.script_model.make_blocks()
        assert set(blocks) == set(self.ordered_blocks)

    @patch("codemodel.script_model.get_instance_dependencies",
           lambda inst: inst.dependencies)
    def test_instance_order(self):
        script_model = self._make_model(is_reversed=False)
        instance_order = script_model.instance_order()
        assert instance_order == self.instance_order

    def test_order_blocks(self):
        # random.sample creates a new list; random.shuffle is in-place!
        blocks = random.sample(self.ordered_blocks,
                               k=len(self.ordered_blocks))
        ordered_blocks = self.script_model.order_blocks(blocks,
                                                        self.instance_order)

        assert ordered_blocks == self.ordered_blocks

    @patch("codemodel.script_model.get_instance_dependencies",
           lambda inst: inst.dependencies)
    def test_draft_script(self):
        script_model = self._make_model(is_reversed=False)
        expected = "\n" + "".join(b.code for b in self.ordered_blocks)
        assert script_model.draft_script() == expected

    @patch("codemodel.script_model.get_instance_dependencies",
           lambda inst: inst.dependencies)
    def test_draft_script_pre_block_hooks(self):
        def pre_hook(old, new):
            return "\n" if old and old.section != new.section else ""

        expected = "\n" + "\n".join(["bar_10baz_10", "foo_50bar_50baz_50",
                                     "bar_90"])
        script_model = self._make_model(is_reversed=False)
        script_model.pre_block_hooks = [pre_hook]
        assert script_model.draft_script() == expected


def test_isort_formatter():
    formatter = ISortFormatter()
    input_code = "import sys\nimport os\n"
    output_code = "import os\nimport sys\n"
    assert formatter(input_code) == output_code

def test_black_formatter():
    formatter = BlackFormatter()
    input_code = "print ('foo')\nbar=baz(qux = 4)"
    output_code = "print(\"foo\")\nbar = baz(qux=4)\n"
    assert formatter(input_code) == output_code
