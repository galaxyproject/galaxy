import os
from typing import (
    Dict,
    Optional,
    TextIO,
)

try:
    from edam_ontology.streams import tabular_stream
except ImportError:
    tabular_stream = None

EDAM_PREFIX = "http://edamontology.org/"

ROOT_OPERATION = "operation_0004"
ROOT_TOPIC = "topic_0003"


def load_edam_tree(path: Optional[str] = None, *included_terms: str):
    if path is not None:
        assert os.path.exists(path), f"Failed to load EDAM tabular data at [{path}] path does not exist."
        handle = open(path)
    else:
        assert (
            tabular_stream is not None
        ), "Failed to load optional import from edam-ontology package, install using [pip install edam-ontology]."
        handle = tabular_stream()
    return load_edam_tree_from_tsv_stream(handle, *included_terms)


def load_edam_tree_from_tsv_stream(tsv_stream: TextIO, *included_terms: str):
    edam: Dict[str, Dict] = {}

    def _recurse_edam_parents(term, path=None):
        if edam[term]["parents"] and len(edam[term]["parents"]) > 0:
            for parent in edam[term]["parents"]:
                yield from _recurse_edam_parents(parent, path + [parent])
        else:
            yield path

    is_first = True
    for line in tsv_stream.readlines():
        fields = line.split("\t")
        if is_first:
            columns = {}
            for i, field in enumerate(fields):
                columns[field] = i
            is_first = False

            definition_column = columns["http://www.geneontology.org/formats/oboInOwl#hasDefinition"]
            term_column = columns["Class ID"]
            label_column = columns["Preferred Label"]
            parents_column = columns["Parents"]
            continue

        term = fields[term_column]
        if not term.startswith(EDAM_PREFIX):
            continue

        term_id = term[len(EDAM_PREFIX) :]

        # Only care about included terms
        if included_terms and not (term_id.startswith(included_terms)):
            continue

        parents = fields[parents_column].split("|")
        edam[term_id] = {
            "label": fields[label_column].strip('"'),
            "definition": fields[definition_column].strip('"'),
            "parents": [x[len(EDAM_PREFIX) :] for x in parents if x.startswith(EDAM_PREFIX)],
        }

    for term in sorted(edam.keys()):
        tails = []
        for x in _recurse_edam_parents(term, path=[]):
            if x[-2:] not in tails:
                tails.append(x[-2:])
        edam[term]["path"] = tails

    return edam


__all__ = ("load_edam_tree", "ROOT_OPERATION", "ROOT_TOPIC")
