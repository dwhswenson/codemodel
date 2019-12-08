import ast
import functools
import importlib
import typing

import astor

import codemodel
import codemodel.asttools as asttools

class UserAST(typing.NamedTuple):
    ast_maker: typing.Callable[[typing.Dict[str, ast.AST], str], ast.AST]
    inputs: typing.List[str]
    outputs: typing.List[str]


class MainCallAST(typing.NamedTuple):
    ast_maker: typing.Callable[[typing.Dict[str, ast.AST], str], ast.Module]
    inputs: typing.List[str]

class GenericFunctionAST(typing.NamedTuple):
    ast_maker: typing.Callable[[typing.Dict[str, ast.AST]], ast.Module]
    inputs: typing.List[str]
    outputs: typing.List[str]

class CodeModel(object):
    """Model for a callable.

    In simple cases, all you need is an instance of this for each
    function/class.

    Parameters
    ----------
    name : str
        the name of the callable that this represents
    parameters : list of :class:`.Parameter`
        the parameters for this callable
    package : :class:`.Package`
        the package where this callable is found
    setup : func or dict
        the function(s) used to instantiate this object; if None (default)
        is just uses the callable that this represents. See docs for more
        details.
    ast_sections : dict
        keys are section numbers as in ``setup``, values are a 2-tuple of
        the AST for the code and the list of variables names to export to
        the script namespace.
    """
    def __init__(self, name, parameters, package=None, setup=None,
                 ast_sections=None):
        self.name = name
        self.parameters = parameters
        self.package = package

        self.setup = self._set_setup(setup, package)
        if self.package and self.setup == {50: self.func}:
            self._pre_call, self._main_call, self._post_call = \
                    [], self.func, []
        else:
            self._pre_call, self._main_call, self._post_call = \
                    self._call_func_order(self.setup)

        if ast_sections is None:
            ast_sections = {}

        ast_setup = {} if self.setup is None else self.setup
        self._ast_funcs = self._set_ast_sections(ast_sections, ast_setup)


    def _set_setup(self, setup, package):
        """set the value of self.setup"""
        if package is None and setup is None:
            return None

        if setup is None:
            setup = {50: self.func}
        elif callable(setup):
            setup = {50: setup}

        return setup

    def _set_ast_sections(self, ast_sections, setup):
        """create partials for AST writing"""
        # TODO: may change some of this significantly, in order to also get
        # output information (which allows significant validation at
        # initialization for setup-function based approaches, and may be
        # required for sanity in AST-based approaches).
        ast_sections = dict(ast_sections)  # copy
        missing = [idx for idx in setup if idx not in ast_sections]
        for sec_id in missing:
            func = setup[sec_id]
            # safety here in case self.func doesn't exist (no `package`)
            self_func = self.func if self.package else None
            if func == self_func:
                # special here because we don't want to look *inside* the
                # code of self.func, and wrappers wouldn't use explicit
                # params -- plus, can override this func in a subclass
                sec_ast = self._default_setup_ast
                outputs = None
            elif func == self._main_call:
                sec_ast = functools.partial(
                    asttools.instantiation_func_to_ast,
                    func=func
                )
                outputs = None
            else:
                sec_ast = functools.partial(
                    asttools.return_dict_func_to_ast_body,
                    func=func
                )

            ast_sections[sec_id] = sec_ast

        return ast_sections

    @staticmethod
    def _call_func_order(setup):
        if setup is None:
            return (None, None, None)

        funcs, trees = zip(*[(func, asttools.func_to_body_tree(func))
                             for (_, func) in sorted(list(setup.items()))])
        funcs, trees = list(funcs), list(trees)
        non_dict_return = [f for (f, tree) in zip(funcs, trees)
            if not asttools.is_return_dict_func(tree)
        ]
        if len(non_dict_return) != 1:
            raise ValueError(("Unable to identify main call function. "
                              + "Found %d non-dict returning "
                              + "functions.") % len(non_dict_return))
        main_call = non_dict_return[0]
        idx = funcs.index(main_call)
        pre_call = funcs[:idx]
        post_call = funcs[idx+1:]
        # TODO: validate each of the functions here
        return (pre_call, main_call, post_call)


    def __hash__(self):
        myhash = hash((self.name, tuple(self.parameters)))
        if self.package:
            # need a special hash here otherwise we get recursion
            myhash = hash((myhash, self.package.name,
                           self.package.import_statement,
                           len(self.package.callables)))
        return myhash


    def __eq__(self, other):
        if self.package == other.package:
            return hash(self) == hash(other)
        elif self.package is None or other.package is None:
            return hash((self.name, tuple(self.parameters))) == \
                    hash((other.name, tuple(other.parameters)))
        else:
            return False  # definitely from different packages!

    def __repr__(self):  # no-cover
        repr_str = ("CodeModel(name={c.name}, parameters={c.parameters} "
                    + "package={c.package})")
        return repr_str.format(c=self)

    # to_dict and from_dict are  not designed for generalized nesting
    # because, well, why make the effort?
    def to_dict(self):
        package_name = self.package.name if self.package else None
        return {'name': self.name,
                'parameters': [p.to_dict() for p in self.parameters]}

    @classmethod
    def from_dict(cls, dct, package=None):
        dct = dict(dct)  # make a copy
        params = [codemodel.Parameter.from_dict(p) for p in dct['parameters']]
        dct['parameters'] = params
        return cls(**dct, package=package)

    @property
    def func(self):
        """the callable for this code model"""
        if not self.package:
            raise RuntimeError("Can't get function without `package` set")
        imports_dict = asttools.import_names(self.package.import_statement)
        imported_modules = {name: importlib.import_module(mod)
                            for name, mod in imports_dict.items()}
        func = getattr(imported_modules[self.package.implicit_prefix],
                       self.name)
        return func

    def instantiate(self, instance):
        """Create an instance of the modeled object.

        Parameters
        ----------
        instance : :class:`.Instance`
            codemodel Instance with appropriate details for this instance

        Returns
        -------
        object :
            whatever the internal callable returns
        """
        setup = self.setup if self.setup else {50: self.func}

        func_param_dict = dict(instance.param_dict)  # copy

        def run_return_dict_func(func, func_param_dict):
            args, kwargs = asttools.get_args_kwargs(func, func_param_dict)
            passthrough = asttools.get_unused_params(func, func_param_dict)
            func_param_dict = func(*args, **kwargs)
            func_param_dict.update(passthrough)
            return func_param_dict

        for func in self._pre_call:
            # func_param_dict = func(**func_param_dict)
            func_param_dict = run_return_dict_func(func, func_param_dict)

        obj = self._main_call(**func_param_dict)

        for func in self._post_call:
            func_param_dict = run_return_dict_func(func, func_param_dict)
            # func_param_dict = func(**func_param_dict)

        return obj

    def _default_setup_ast(self, param_dict, assign=None):
        return asttools.create_call_ast(self.func, param_dict,
                                        assign=assign,
                                        prefix=self.package.implicit_prefix)

    def instance_ast_sections(self, instance):
        # TODO: add the to_ast function
        params = dict(instance.param_dict)
        params_ast = {name: to_ast(param)
                      for name, param in instance.param_dict.items()}
        ast_sections = {}
        ast_funcs = self._ast_funcs
        for sec_id, func in self.setup.items():
            if func == self._main_call:
                sec_ast = ast_funcs[sec_id](params_ast, assign=instance.name)
            else:
                sec_ast = ast_funcs[sec_id](params_ast)
            ast_sections[sec_id] = sec_ast

        return ast_sections

    def code_sections(self, instance):
        """ """
        return {k: astor.to_source(v) for
                k, v in self.instance_ast_sections(instance).items()}


def to_ast(obj):
    if isinstance(obj, Instance):
        node = ast.Name(id=obj.code_name, ctx=ast.Load())
    else:
        # TODO: this can probably be improved
        node = ast.parse(repr(obj), mode='eval').body
    return node


class Instance(object):
    validator = codemodel.type_validation.DEFAULT_VALIDATOR
    """Representation of an instance (noun-like object) in the source.

    In particular, this gives us access to the important values:

    Parameters
    ----------
    """
    def __init__(self, name, code_model, param_dict):
        self.name = name
        self._code_name = None
        self.code_model = code_model
        self.param_dict = param_dict
        self._instance = None

    @property
    def instance(self):
        """functional version of the instance this represents"""
        if self._instance is None:
            self._instance = self.code_model.instantiate(self)
        return self._instance

    @property
    def code_name(self):
        if self._code_name:
            return self._code_name
        else:
            return self.name

    @code_name.setter
    def code_name(self, value):
        self._code_name = value

    @property
    def code_sections(self):
        """code for this instance, as a sections dictionary"""
        return self.code_model.code_sections(self)

    def __str__(self):  # no-cover
        return self.code_name
