"""Path manipulation functions.
"""
from __future__ import absolute_import

import errno
import imp
from functools import partial
from itertools import starmap
from operator import getitem
from os import (
    makedirs,
    walk,
)
from os.path import (
    abspath,
    exists,
    isabs,
    join,
    normpath,
    pardir,
    realpath,
    relpath,
)

from six import string_types
from six.moves import filterfalse, map, zip


def safe_contains(prefix, path, whitelist=None):
    """Ensure a path is contained within another path.

    Given any two filesystem paths, ensure that ``path`` is contained in ``prefix``. If ``path`` exists (either as an
    absolute path or relative to ``prefix``), it is canonicalized with :func:`os.path.realpath` to ensure it is not a
    symbolic link that points outside of ``prefix``. If it is a symbolic link and ``whitelist`` is set, the symbolic link
    may also point inside a ``whitelist`` path.

    The ``path`` is checked against ``whitelist`` using either its absolute pathname (if passed in as absolute) or
    relative to ``prefix`` and canonicalized (if applicable). It is *not* ``os.path.join()``ed with each ``whitelist``
    directory.

    :type prefix:       string
    :param prefix:      a directory under which ``path`` is to be checked
    :type path:         string
    :param path:        a filename to check
    :type whitelist:    list of strings
    :param whitelist:   list of additional paths under which ``path`` may be located
    :rtype:             bool
    :returns:           ``True`` if ``path`` is contained within ``prefix`` or ``whitelist``, ``False`` otherwise.
    """
    return any(__contains(prefix, path, whitelist=whitelist))


def safe_makedirs(path):
    """Safely make a directory, do not fail if it already exists or is created during execution.

    :type path:     string
    :param path:    a directory to create
    """
    # prechecking for existence is faster than try/except
    if not exists(path):
        try:
            makedirs(path)
        except OSError as e:
            # reviewing the source for Python 2.7, this would only ever happen for the last path element anyway so no
            # need to recurse - this exception means the last part of the path was already in existence.
            if e.errno != errno.EEXIST:
                raise


def safe_relpath(path):
    """Determine whether a relative path references a path outside its root.

    This is a path computation: the filesystem is not accessed to confirm the existence or nature of ``path``.

    :type path:     string
    :param path:    a path to check
    :rtype:         bool
    :returns:       ``True`` if path is relative and does not reference a path in a parent directory, ``False``
                    otherwise.
    """
    return not (isabs(path) or normpath(path).startswith(pardir))


def unsafe_walk(path, whitelist=None):
    """Walk a path and ensure that none of its contents are symlinks outside the path.

    It is assumed that ``path`` itself has already been validated e.g. with :func:`safe_relpath` or
    :func:`safe_contains`.

    :type path:         string
    :param path:        a directory to check for unsafe contents
    :type whitelist:    list of strings
    :param whitelist:   list of additional paths under which contents may be located
    :rtype:             iterator
    :returns:           Iterator of "bad" files found under ``path``
    """
    return filterfalse(partial(safe_contains, path, whitelist=whitelist), __walk(abspath(path)))


def __listify(item):
    """A non-splitting version of :func:`galaxy.util.listify`.
    """
    if not item:
        return []
    elif isinstance(item, list) or isinstance(item, tuple):
        return item
    else:
        return [item]


# helpers


def __walk(path):
    for dirpath, dirnames, filenames in walk(path):
        for name in dirnames + filenames:
            yield join(dirpath, name)


def __contains(prefix, path, whitelist=None):
    real = realpath(join(prefix, path))
    yield not relpath(real, prefix).startswith(pardir)
    for wldir in whitelist or []:
        yield not relpath(real, wldir).startswith(pardir)


# cross-platform support


def _build_self(target, path_module):
    """Populate a module with the same exported functions as this module, but using the given os.path module.

    :type target: module
    :param target: module on which to set ``galaxy.util.path`` functions
    :type path_module: ``ntpath`` or ``posixpath`` module
    :param path_module: module implementing ``os.path`` API to use for path functions
    """
    __copy_self().__set_fxns_on(target, path_module)


def __copy_self(names=__name__, parent=None):
    """Returns a copy of this module that can be modified without modifying `galaxy.util.path`` in ``sys.modules``.
    """
    if isinstance(names, string_types):
        names = iter(names.split('.'))
    try:
        name = names.next()
    except StopIteration:
        return parent
    path = parent and parent.__path__
    parent = imp.load_module(name, *imp.find_module(name, path))
    return __copy_self(names, parent)


def __set_fxns_on(target, path_module):
    """Overrides imported os.path functions with the ones from path_module and populates target with the global
    functions from this module.
    """
    for name in __pathfxns__:
        globals()[name] = getattr(path_module, name)
    __get = partial(getitem, globals())
    __set = partial(setattr, target)
    # this is actually izip(..., imap(...))
    __fxns = zip(__all__, map(__get, __all__))
    # list() to execute
    list(starmap(__set, __fxns))


__pathfxns__ = (
    'abspath',
    'exists',
    'isabs',
    'join',
    'normpath',
    'pardir',
    'realpath',
    'relpath',
)

__all__ = (
    'safe_contains',
    'safe_makedirs',
    'safe_relpath',
    'unsafe_walk',
)
