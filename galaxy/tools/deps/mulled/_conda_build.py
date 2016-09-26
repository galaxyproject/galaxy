"""Compat. layer with conda_build if not installed through conda."""
import os
import yaml


try:
    from conda_build.metadata import MetaData
except ImportError:

    class MetaData(object):

        def __init__(self, input_dir):
            recipe_path = os.path.join(input_dir, "meta.yaml")
            self.input_dir = input_dir
            with open(recipe_path, "r") as f:
                self.meta = yaml.load(f)

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


__all__ = ["MetaData"]
