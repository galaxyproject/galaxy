"""Path manipulation functions.
"""
from __future__ import absolute_import

import errno
import imp
import logging
from functools import partial
try:
    from grp import getgrgid
except ImportError:
    getgrgid = None
from itertools import starmap
from operator import getitem
from os import (
    extsep,
    makedirs,
    stat,
    walk
)
from os.path import (
    abspath,
    dirname,
    exists,
    isabs,
    join,
    normpath,
    pardir,
    realpath,
    relpath,
    sep as separator,
)
try:
    from pwd import getpwuid
except ImportError:
    getpwuid = None

from six import iteritems, string_types
from six.moves import map, zip
log = logging.getLogger(__name__)


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


def unsafe_walk(path, whitelist=None, username=None):
    """Walk a path and ensure that none of its contents are symlinks outside the path.

    It is assumed that ``path`` itself has already been validated e.g. with :func:`safe_relpath` or
    :func:`safe_contains`.

    :type path:         string
    :param path:        a directory to check for unsafe contents
    :type whitelist:    list of strings
    :param whitelist:   list of additional paths under which contents may be located
    :rtype:             list of strings
    :returns:           A list of "bad" files found under ``path``
    """
    unsafe_paths = []
    for walked_path in __walk(abspath(path)):
        is_safe = safe_contains(path, walked_path, whitelist=whitelist)
        if username and is_safe:
            is_safe = full_path_permission_for_user(path, walked_path, username=username, skip_prefix=True)
        if not is_safe:
            unsafe_paths.append(walked_path)
    return unsafe_paths


def __path_permission_for_user(path, username):
    """
    :type path:         string
    :param path:        a directory or file to check
    :type username:     string
    :param username:    a username matching the systems username
    """
    if getpwuid is None:
        raise NotImplementedError("This functionality is not implemented for Windows.")

    group_id_of_file = stat(path).st_gid
    file_owner = getpwuid(stat(path).st_uid)
    group_members = getgrgid(group_id_of_file).gr_mem

    oct_mode = oct(stat(path).st_mode)
    owner_permissions = int(oct_mode[-3])
    group_permissions = int(oct_mode[-2])
    other_permissions = int(oct_mode[-1])
    if other_permissions >= 4 or \
            (file_owner == username and owner_permissions >= 4) or \
            (username in group_members and group_permissions >= 4):
        return True
    return False


def full_path_permission_for_user(prefix, path, username, skip_prefix=False):
    """
    Assuming username is identical to the os username, this checks that the
    given user can read the specified path by checking the file permission
    and each parent directory permission.

    :type prefix:       string
    :param prefix:      a directory under which ``path`` is to be checked
    :type path:         string
    :param path:        a filename to check
    :type username:     string
    :param username:    a username matching the systems username
    :type skip_prefix:  bool
    :param skip_prefix: skip the given prefix from being checked for permissions

    """
    full_path = realpath(join(prefix, path))
    top_path = realpath(prefix) if skip_prefix else None
    can_read = __path_permission_for_user(full_path, username)
    if can_read:
        depth = 0
        max_depth = full_path.count(separator)
        parent_path = dirname(full_path)
        while can_read and depth != max_depth:
            if parent_path in [separator, top_path]:
                break
            if not __path_permission_for_user(parent_path, username):
                can_read = False
            depth += 1
            parent_path = dirname(parent_path)
    return can_read


def joinext(root, ext):
    """
    Roughly the reverse of os.path.splitext.

    :type  root: string
    :param root: part of the filename before the extension
    :type  root: string
    :param ext: the extension
    :rtype: string
    :returns: ``root`` joined with ``ext`` separated by a single ``os.extsep``
    """
    return extsep.join([root.rstrip(extsep), ext.lstrip(extsep)])


def has_ext(path, ext, aliases=False, ignore=None):
    """
    Determine whether ``path`` has extension ``ext``

    :type     path: string
    :param    path: Path to check
    :type      ext: string
    :param     ext: Extension to check
    :type  aliases: bool
    :param aliases: Check any known aliases for the given extension
    :type   ignore: string
    :param  ignore: Ignore this extension at the end of the path (e.g. ``sample``)
    :rtype:         bool
    :returns:       ``True`` if path is a YAML file, ``False`` otherwise.
    """
    ext = __ext_strip_sep(ext)
    root, _ext = __splitext_ignore(path, ignore=ignore)
    if aliases:
        return _ext in extensions[ext]
    else:
        return _ext == ext


def get_ext(path, ignore=None, canonicalize=True):
    """
    Return the extension of ``path``

    :type          path: string
    :param         path: Path to check
    :type        ignore: string
    :param       ignore: Ignore this extension at the end of the path (e.g. ``sample``)
    :type  canonicalize: bool
    :param canonicalize: If the extension is known to this module, return the canonicalized extension instead of the
                         file's actual extension
    :rtype:              string
    """
    root, ext = __splitext_ignore(path, ignore=ignore)
    if canonicalize:
        try:
            ext = extensions.canonicalize(ext)
        except KeyError:
            pass  # should do something else here?
    return ext


class Extensions(dict):
    """Mappings for extension aliases.

    A dict-like object that returns values for keys that are not mapped if the key can be found in any of the dict's
    values (which should be sequence types).

    The first item in the sequence should match the key and is the "canonicalization".
    """
    def __missing__(self, key):
        for k, v in iteritems(self):
            if key in v:
                self[key] = v
                return v
        raise KeyError(key)

    def canonicalize(self, ext):
        # shouldn't raise an IndexError because it should raise a KeyError first
        return self[ext][0]


extensions = Extensions({
    'ini': ['ini'],
    'json': ['json'],
    'yaml': ['yaml', 'yml'],
})


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


def __ext_strip_sep(ext):
    return ext.lstrip(extsep)


def __splitext_no_sep(path):
    return (path.rsplit(extsep, 1) + [''])[0:2]


def __splitext_ignore(path, ignore=None):
    # note: unlike os.path.splitext this strips extsep from ext
    ignore = map(__ext_strip_sep, __listify(ignore))
    root, ext = __splitext_no_sep(path)
    if ext in ignore:
        new_path = path[0:(-len(ext) - 1)]
        root, ext = __splitext_no_sep(new_path)

    return (root, ext)


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
        name = next(names)
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
    'extensions',
    'get_ext',
    'has_ext',
    'joinext',
    'safe_contains',
    'safe_makedirs',
    'safe_relpath',
    'unsafe_walk',
)
