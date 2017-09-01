"""Path manipulation functions
"""
from __future__ import absolute_import

from os import extsep, pardir, sep
from os.path import normpath

from six import iteritems, string_types

from ..util import listify


def safe_relpath(path):
    """
    Given what we expect to be a relative path, determine whether the path would exist inside the current directory.

    :type   path:   string
    :param  path:   a path to check
    :rtype:         bool
    :returns:       ``True`` if path is relative and does not reference a path in a parent directory, ``False`` otherwise.
    """
    return not (path.startswith(sep) or normpath(path).startswith(pardir))


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


def __ext_strip_sep(ext):
    return ext.lstrip(extsep)


def __splitext_no_sep(path):
    return (path.rsplit(extsep, 1) + [''])[0:2]


def __splitext_ignore(path, ignore=None):
    # note: unlike os.path.splitext this strips extsep from ext
    ignore = map(__ext_strip_sep, listify(ignore, split=False))
    root, ext = __splitext_no_sep(path)
    if ext in ignore:
        root, ext = __splitext_no_sep(path)
    return (root, ext)


__all__ = ('extensions', 'get_ext', 'has_ext', 'joinext', 'safe_relpath')
