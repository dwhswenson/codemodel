import codemodel
import collections

import black  # TODO: make black optional
import isort

Block = collections.namedtuple("Block", "section instance code")

def get_instance_dependencies(instance):
    # get the instances used to create another instance
    # TODO: maybe give this the ability to recurse into lists later?
    dependencies = []
    param_dict = instance.param_dict
    to_search = list(param_dict.values())
    while to_search:
        item = to_search.pop(0)
        if isinstance(item, codemodel.Instance):
            dependencies.append(item)
        # elif ismappable, isiterable
    return dependencies

class BlackFormatter(object):
    def __init__(self, mode=None):
        if mode is None:
            mode = black.FileMode()
        self.mode = mode

    def __call__(self, script):
        return black.format_file_contents(script, fast=False,
                                          mode=self.mode)

class ISortFormatter(object):
    # this is a class in order to allow configuration in the future
   def __call__(self, script):
       return isort.code(code=script)


class ScriptModel(object):
    def __init__(self, order_callback=None, pre_block_hooks=None,
                 formatters=None):
        if pre_block_hooks is None:
            pre_block_hooks = []

        if formatters is None:
            # these are defaults; use formatter=[] to get no formatting
            formatters = [
                BlackFormatter(black.FileMode()),
                ISortFormatter(),
            ]

        self.order_callback = order_callback
        self.pre_block_hooks = pre_block_hooks
        self.formatters = formatters
        self.instances = []

    def register_instance(self, instance):
        self.instances.append(instance)

    def make_blocks(self):
        """
        Returns
        -------
        List[Block] :
            block object for all code blocks in this script
        """
        # DEBUG
        # for inst in self.instances:
            # for sec, code in inst.code_sections.items():
                # print(inst, sec)
                # print(code)
        #######
        blocks = [Block(sec, inst, code)
                  for inst in self.instances
                  for sec, code in inst.code_sections.items()]
        return blocks

    def instance_order(self):
        """
        Returns
        -------
        Dict[codemodel.Instance, int] :
            mapping of the instance to its order in the DAG
        """
        dependencies = {instance: get_instance_dependencies(instance)
                        for instance in self.instances}
        dag = codemodel.dag.DAG.from_dependency_dict(dependencies)
        ordered = list(dag.ordered(self.order_callback))
        return {inst: i for (i, inst) in enumerate(ordered)}

    def order_blocks(self, blocks, instance_order):
        """
        Returns
        -------
        List[Block] :
            blocks in order they should appear in the script
        """
        def sort_key(block):
            return block.section, instance_order[block.instance]

        return list(sorted(blocks, key=sort_key))

    def draft_script(self):
        """Create the rough script from the registered instances

        Typically, you'll actually want to use :meth:`.get_script`, which
        passes this rough script through the external code formatters.
        """
        blocks = self.make_blocks()
        instance_order = self.instance_order()
        ordered_blocks = self.order_blocks(blocks, instance_order)

        packages = set([inst.code_model.package for inst in self.instances])
        imports = [p.import_statement for p in packages if p is not None]

        script = "\n".join(imports) + "\n"
        prev_block = None
        for block in ordered_blocks:
            for hook in self.pre_block_hooks:
                script += hook(prev_block, block)

            script += block.code
            prev_block = block

        return script

    def get_script(self):  # no-cover
        """Generate the formatted Python script."""
        # so trivial that we don't include in tests
        script = self.draft_script()
        for formatter in self.formatters:
            script = formatter(script)

        return script
