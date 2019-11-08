import json
import inspect

import codemodel

# extend this if you subclass CodeModel
CODEMODEL_TYPES = {'CodeModel': codemodel.CodeModel}

class Parameter(object):
    """A parameter in a callable.

    Wrapper around inspect.Parameter, with our own param_type and desc
    (instead of the standard Python annotations). The whole thing can be
    JSON-serialized by way of a dictionary.

    Parameters
    ----------
    parameter : inspect.Parameter
        description of the parameter
    param_type : str
        parameter type
    desc: str
        string description of this parameter
    """
    def __init__(self, parameter, param_type, desc=None):
        self.parameter = parameter
        self.param_type = param_type
        self.desc = desc

    def __repr__(self):  # no-cover
        return "Parameter({p}, param_type={t}, desc={d})".format(
            p=repr(self.parameter),
            t=self.param_type,
            d=self.desc
        )

    def __hash__(self):
        return hash((self.parameter, self.param_type, self.desc))

    def __eq__(self, other):
        return hash(self) == hash(other)

    @classmethod
    def from_values(cls, name, param_type, desc=None,
                    kind="POSITIONAL_OR_KEYWORD",
                    default=inspect.Parameter.empty):
        parameter = inspect.Parameter(
            name=name,
            kind=getattr(inspect.Parameter, kind),
            default=default
        )
        return cls(parameter, param_type, desc)

    @property
    def name(self):
        return self.parameter.name

    @property
    def default(self):
        if self.has_default:
            return self.parameter.default
        else:
            return None

    @property
    def has_default(self):
        return self.parameter.default is not inspect.Parameter.empty

    def to_dict(self):
        return {
            'name': self.name,
            'param_type': self.param_type,
            'kind': str(self.parameter.kind),
            'has_default': self.has_default,
            'default': self.default,
            'desc': self.desc
        }

    @classmethod
    def from_dict(cls, dct):
        dct = dict(dct)  # copy
        has_default = dct.pop('has_default')
        if not has_default:
            dct['default'] = inspect.Parameter.empty
        return cls.from_values(**dct)

    def validate_input(self, inp, validator=None):
        pass


class Package(object):
    def __init__(self, name, callables, import_statement=None,
                 implicit_prefix=None, model_types=None):
        """Container for CodeModel callables, representing a package.

        Parameters
        ----------
        name : str
            package name
        callables : list of :class:`.CodeModel`
            callables contained in this package
        import_statement : str
            the statemetn used to import the package (e.g., "import sys" or
            "from os import path")
        implicit_prefix: str
            callables are prefixed with this after the import statement,
            e.g., "import os" as import statement would makethis "os"
        model_types : list of str
            string names for CodeModel subclass to be used; one for each
            callable. Only relevant in event of subclassing.
        """
        if implicit_prefix is None:
            implicit_prefix = ""

        if model_types is None:
            model_types = ["CodeModel"] * len(callables)

        self.name = name
        self.import_statement = import_statement
        self.implicit_prefix = implicit_prefix
        self.callables = callables
        self.model_types = model_types

    def __hash__(self):
        return hash((self.name, self.import_statement, self.implicit_prefix,
                     tuple(self.model_types), tuple(self.callables)))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def to_dict(self):
        return {'name': self.name,
                'import_statement': self.import_statement,
                'implicit_prefix': self.implicit_prefix,
                'model_types': self.model_types,
                'callables': [c.to_dict() for c in self.callables]
        }

    @classmethod
    def from_dict(cls, dct):
        dct = dict(dct)  # copy
        dct['callables'] = [
            CODEMODEL_TYPES[model_t].from_dict(call_dct)
            for model_t, call_dct in zip(dct['model_types'], dct['callables'])
        ]
        return cls(**dct)


def load_json(filename):
    with open(filename, mode='r') as f:
        dct = json.load(f)

    return Package.from_dict(dct)
