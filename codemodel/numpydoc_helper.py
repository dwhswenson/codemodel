import inspect
from numpydoc.docscrape import ClassDoc, FunctionDoc
def numpydoc_type_desc(thing):
    if inspect.isfunction(thing) or inspect.ismethod(thing):
        docs = FunctionDoc(thing)
    elif inspect.isclass(thing):
        docs = ClassDoc(thing)
    else:
        raise RuntimeError("Don't know how to handle " + repr(thing))

    npdoc_params = docs["Parameters"]
    types = [p.type for p in npdoc_params]
    descs = [" ".join(p.desc) for p in npdoc_params]
    return types, descs
