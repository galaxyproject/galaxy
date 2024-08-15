# TODO: ---- This is a work in progress ----
"""
Dataproviders are iterators with context managers that provide data to some
consumer datum by datum.

As well as subclassing and overriding to get the proper data, Dataproviders
can be piped from one to the other.

.. note:: be careful to NOT pipe providers into subclasses of those providers.
    Subclasses provide all the functionality of their superclasses,
    so there's generally no need.

.. note:: be careful to when using piped providers that accept the same keywords
    in their __init__ functions (such as limit or offset) to pass those
    keywords to the proper (often final) provider. These errors that result
    can be hard to diagnose.
"""
from . import (
    base,
    chunk,
    column,
    dataset,
    decorators,
    exceptions,
    external,
    hierarchy,
    line,
)

__all__ = ("decorators", "exceptions", "base", "chunk", "line", "hierarchy", "column", "external", "dataset")
