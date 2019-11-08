import importlib

import codemodel
from codemodel import imports, asttools

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
    """
    def __init__(self, name, parameters, package=None, setup=None,
                 ast_sections=None):
        self.name = name
        self.parameters = parameters
        self.package = package

        if self.package is None and setup is None:
            setup = {}

        if ast_sections is not None:
            # TODO: maybe bind it? https://stackoverflow.com/a/1015405
            ...

        if setup is None:
            setup = {50: self.func}
        elif callable(setup):
            setup = {50: setup}

        self.setup = setup

        # TODO: separate this stuff?
        if self.setup:
            funcs = [func for (_, func) in sorted(list(self.setup.items()))]
            non_dict_return = [f for f in funcs
                               if not asttools.is_return_dict_function(f)]
            if len(non_dict_return) != 1:
                raise ValueError("Unable to identify instantiation ",
                                 " function. Found %d non-dict returning ",
                                 " functions." % len(non_dict_return))
            self._instantiator = non_dict_return[0]
            idx = funcs.index(self._instantiator)
            self._pre_instantiator = funcs[:idx]
            self._post_instantiator = funcs[idx+1:]
            # TODO: validate each of the functions here


    def __hash__(self):
        return hash((self.name, tuple(self.parameters), self.package))

    def __eq__(self, other):
        return hash(self) == hash(other)

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
        imports_dict = imports.import_names(self.package.import_statement)
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

        for func in self._pre_instantiator:
            # TODO: fix this for positional arguments
            func_param_dict = func(**func_param_dict)

        obj = self._instantiator(**func_param_dict)

        for func in self._post_instantiator:
            func_param_dict = func(**func_param_dict)

        return obj

    def _default_setup_ast(self, param_dict, assign=None):
        return asttools.default_ast(self.func, param_dict,
                                    prefix=self.prefix, assign=assign)

    def ast_sections(self, instance):
        params = dict(instance.param_dict)
        ast_sections = {}
        for sec_id, func in self.setup.items():
            if func == self.func:
                # special here because we don't want to look *inside* the
                # code of self.func, and wrappers wouldn't use explicit
                # params -- plus, can override this func in a subclass
                sec_ast = self._default_setup_ast(param_dict,
                                                  assign=instance.name)
            elif func == self._instantiator:
                sec_ast = ...  # general case for instantiators
            else:
                sec_ast, params = ...  # parse in other cases
            ast_sections[sec_id] = sec_ast

        return ast_sections

    def code_sections(self, instance):
        """ """
        return {k: astor.to_source(v) for
                k, v in self.ast_sections(instance)}


def _unshadow_property_error(self, item):
    # I know I'd seen this problem before
    dct = self.__class__.__dict__
    if item in dct:
        p = dct[item]
        if isinstance(p, property):
            try:
                result = p.fget(self)
            except:
                raise
            else:
                return result  # miraculously fixed
                # alternately, complain
                # raise AttributeError(
                    # "Unknown problem occurred in property"
                    # + str(p.fget.__name__) + ": Second attempt returned"
                    # + str(result)
                # )

class Instance(object):
    """Representation of an instance (noun-like object) in the source.

    In particular, this gives us access to the important values:

    Parameters
    ----------
    """
    def __init__(self, name, code_model, param_dict):
        self.name = name
        self.code_model = code_model
        self.param_dict = param_dict
        self._instance = None

    def __getattr__(self, item):
        # NOTE: getattr in a property can shadow errors
        _unshadow_property_error(self, item)
        try:
            return self.param_dict[item]
        except KeyError:
            raise AttributeError('{cls} has no attribute {item}'.format(
                cls=str(self.__class__),
                item=str(item)
            ))

    @property
    def instance(self):
        if self._instance is None:
            self._instance = self.code_model.instantiate(self)
        return self._instance

    # TODO: add properties for prepare_as_code, setup_as_code,
    @property
    def code_sections(self):
        return self.code_model.code_sections(self)

    def __str__(self):
        return self.name
