"""Compat. layer with conda_build/verify if Galaxy/galaxy-lib not installed through conda.

In general there are utilities available for Conda building and parsing that are high-quality
and should be utilized when available but that are only available in conda channels and not in
PyPI. This module serves as a PyPI capable interface to these utilities.
"""
import os
from collections.abc import Hashable

import yaml

try:
    from conda_build.metadata import MetaData
except ImportError:
    MetaData = None

try:
    from anaconda_verify.recipe import parse, render_jinja2
except ImportError:
    render_jinja2 = None
    parse = None


class _Memoized:

    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value


def _parse(data, cfg):
    """Parse metadata YAML."""
    assert cfg is None, "Conda utilities for evaluating cfg are not available."
    return dict(yamlize(data))


def _render_jinja2(recipe_dir):
    """Evaluate Conda recipe as a jinja template."""
    try:
        import jinja2
    except ImportError:
        raise Exception("Failed to import jinja2 for evaluating Conda recipe templates.")

    loaders = [jinja2.FileSystemLoader(recipe_dir)]
    env = jinja2.Environment(loader=jinja2.ChoiceLoader(loaders))
    template = env.get_or_select_template('meta.yaml')
    return template.render(environment=env)


@_Memoized
def yamlize(data):
    res = yaml.safe_load(data)
    # ensure the result is a dict
    if res is None:
        res = {}
    return res


if render_jinja2 is None:
    render_jinja2 = _render_jinja2

if parse is None:
    parse = _parse


def raw_metadata(recipe_dir):
    """Evaluate Conda template if needed and return raw metadata for supplied recipe directory."""
    meta_path = os.path.join(recipe_dir, 'meta.yaml')
    with open(meta_path, 'rb') as fi:
        data = fi.read()
        if b'{{' in data:
            data = render_jinja2(recipe_dir)
    meta = parse(data, None)
    return meta


class _MetaData:

    def __init__(self, input_dir):
        self.meta = raw_metadata(input_dir)

    def get_value(self, field, default=None):
        """Get nested field value or supplied default is not present."""
        section, key = field.split('/')
        submeta = self.meta.get(section)
        if submeta is None:
            submeta = {}
        res = submeta.get(key)
        if res is None:
            res = default
        return res


if MetaData is None:
    MetaData = _MetaData

__all__ = (
    "MetaData",
    "raw_metadata",
)
