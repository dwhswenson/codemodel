import ast
import codemodel

class Instance(object):
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
        self.param_type = {p.name: p.param_type
                           for p in self.code_model.parameters}
        self._instance = None

    def param_dict_validation(self, **instance_kwargs):
        # instance_kwargs are extra kwargs needed to instantiate that don't
        # come directly from user input (like stuff built in the dag)
        param_dict = dict(**self.param_dict, **instance_kwargs)
        for p in param_dict:
            ptype = self.param_type.get(p, 'instance')
            # TODO: switch from assert
            assert self.code_model.validator[p_type].validate(param_dict[p])
        return param_dict

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

