import inspect
import codemodel
import importlib


def default_type_desc(func):
    """Default tool to extract type and description.

    Type is always "Unknown", description is always None. Use a more
    intelligent function than this with the same signature to do anything
    interesting.

    Parameters
    ----------
    func : callable
        a function with a signature

    Returns
    -------
    types : List[str]
        types that can be processed by codemodel for type checking; one for
        each parameter in the signature
    desc : List[Union[str, None]
        descriptions of each parameter or None if no description can be
        determined
    """
    sig = inspect.signature(func)
    results = [("Unknown", None) for p in sig.parameters]
    if not results:
        # if there are no parameters, still need length-2
        return [(), ()]
    return list(zip(*results))


def codemodel_from_callable(func, type_desc=default_type_desc,
                            package=None):
    """Create CodeModel from a callable function

    Parameters
    ----------
    func : Callable[[Any], Any]
        function to create the model of
    type_desc : Callable[[Callable], Tuple[List[str], List[str]]]
        function to extract type and description for each parameter of its
        input callable. See :func:`.default_type_desc`.
    package : Union[:class:`.Package`, None]
        package to register this model with

    Returns
    -------
    :class:`.CodeModel` :
        model for this method; note that if ``package`` is given, this has
        the side-effect of registering the model with the package
    """
    inspect_params = inspect.signature(func).parameters.values()
    name = func.__name__
    param_type, desc = type_desc(func)
    parameters = [
        codemodel.Parameter(p, p_type, desc)
        for p, p_type, desc in zip(inspect_params, param_type, desc)
    ]
    model = codemodel.CodeModel(name, parameters, package=package)
    if package:
        package.register_codemodel(model)
    return model


def package_from_import(import_statement):
    """Create (empty) package from an import statement.

    This determines the name and prefix of the package based on the import
    statement, assuming that the name should be the full import name, and
    the prefix is the import alias used. For example, ``import os`` has name
    and prefix ``os``, while ``from os import path as foo`` has name
    ``os.path`` and prefix ``foo``.

    The resulting package is "empty" in the sense that it has no callables
    associated with it. Callables can be registered after the fact.

    Parameters
    ----------
    import_statement : str
        a valid Python import statement

    Returns
    -------
    :class:`.Pacakge` :
        an empty package to contain callables based on this import
    """
    imports = codemodel.asttools.import_names(import_statement)
    assert len(imports) == 1
    implicit_prefix, name = list(imports.items())[0]
    package = codemodel.Package(name, [], import_statement=import_statement,
                                implicit_prefix=implicit_prefix)
    return package


def make_package(import_statement, callable_names,
                 type_desc=default_type_desc, name=None):
    package = package_from_import(import_statement)
    if name is not None:
        package.name = name
    module = package.module
    for func_name in callable_names:
        func = getattr(module, func_name)
        # the following also registers the model with the package
        model = codemodel_from_callable(func, type_desc=type_desc,
                                        package=package)
    return package
