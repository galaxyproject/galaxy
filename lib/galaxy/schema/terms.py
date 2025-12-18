import yaml

from galaxy.util.resources import resource_string


def load_terms_raw():
    new_data_yaml = resource_string(__name__, "terms.yml")
    terms_raw = yaml.safe_load(new_data_yaml)
    return terms_raw


class HelpTerms:
    def __init__(self):
        self.terms = load_terms_raw()

    def get_term(self, term_path: str) -> str:
        root = self.terms
        for part in term_path.split("."):
            if part not in root:
                raise KeyError(f"Term '{term_path}' not found.")
            root = root[part]
        assert isinstance(root, str), f"Term '{term_path}' is not a string."
        return root
