class FuncSigHolder(object):
    @staticmethod
    def foo_pkw(pkw):
        pass

    def foo_pkw_kw_varkw(pkw, *, kw, **varkw):
        pass

    def foo_pkw_varpos_kw_varkw(pkw, *varpos, kw, **varkw):
        pass

class ValidateFuncHolder(object):
    def dict_return_global(foo):
        return {'foo': bar}

    def valid(foo):
        bar = 1
        return {'foo': foo}

    def valid_foo_changed(foo):
        bar = 1
        return {'foo': foo * 2}

    def no_return(foo):
        bar = 1
        pass

    def return_non_dict(foo):
        bar = 1
        return foo

    def call_something(foo):
        bar = 1
        return baz(foo, bar)


