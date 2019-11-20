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

def nested_scopes():
    def bar():
        if True:
            return 1
        else:
            return 0

    class Baz(object):
        def __init__(qux):
            self._qux = qux

        def qux(self):
            return self.qux

    # q is illegal global
    if q > 3:
        return bar
    elif q < 0:
        return Baz
    return "foo"

def return_dict_tester(a):
    def inner():
        if a > 0:
            return {'bar': 1}
        else:
            return {'qux': 3}

    baz = 'foo'
    if a > 0:
        return {'name': 'positive', 'baz': baz}
    elif a < 0:
        return {'name': 'negative', 'baz': '-'+baz}
    return {'name': 'zero', 'baz': '0'}

def undefined_names_tester(a, b):
    alpha = a + b
    def bar(baz):
        baz += 1
        if baz == alpha:
            return True
        return False
    beta = b - a
    a.purple = b.green
    b = blue
