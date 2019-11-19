import inspect
import codemodel
import importlib


def default_type_desc(func):
    sig = inspect.signature(func)
    results = [("Unknown", None) for p in sig.parameters]
    if not results:
        # if there are no parameters, still need length-2
        return [(), ()]
    return list(zip(*results))


def codemodel_from_callable(func, type_desc=default_type_desc,
                            package=None):
    inspect_params = inspect.signature(func).parameters.values()
    name = func.__name__
    call, desc = type_desc(func)
    parameters = [
        codemodel.Parameter(p, param_type, desc)
        for p, param_type, desc in zip(inspect_params, call, desc)
    ]
    return codemodel.CodeModel(name, parameters, package=package)


def package_from_import(import_statement):
    imports = codemodel.asttools.import_names(import_statement)
    assert len(imports) == 1
    implicit_prefix, name = list(imports.items())[0]
    package = codemodel.Package(name, [], import_statement=import_statement,
                                implicit_prefix=implicit_prefix)
    return package


def make_package(import_statement, callable_names):
    package = package_from_import(import_statement)
    module = importlib.import_module(package.name)
    for func_name in callable_names:
        func = getattr(module, func_name)
        model = codemodel_from_callable(func, package=package)
        package.register_codemodel(model)
    return package
