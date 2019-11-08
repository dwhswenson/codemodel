import importlib

from codemodel import imports

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
    """
    def __init__(self, name, parameters, package=None):
        self.name = name
        self.parameters = parameters
        self.package = package

    # to_dict and from_dict are  not designed for generalized nesting
    # because, well, why make the effort?
    def to_dict(self):
        package_name = self.package.name if self.package else None
        return {'name': self.name,
                'parameters': [p.to_dict() for p in self.parameters],
                'package': package_name}

    @classmethod
    def from_dict(cls, dct, package=None):
        dct = dict(dct)  # make a copy
        params = [codemodel.Parameter.from_dict(p) for p in dct['parameters']]
        dct['parameters'] = params
        if package:
            dct['package'] = package
        return cls(**dct)

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
