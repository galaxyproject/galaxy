import io
import os
from typing import Dict, Optional, TextIO

try:
    from edam_ontology.streams import tabular_stream
except ImportError:
    tabular_stream = None

EDAM_PREFIX = 'http://edamontology.org/'
COLUMN_TERM = 0
COLUMN_LABEL = 1
COLUMN_PARENTS = 7

ROOT_OPERATION = 'operation_0004'
ROOT_TOPIC = 'topic_0003'


def load_edam_tree(path: Optional[str] = None):
    if path is not None:
        assert os.path.exists(path), f"Failed to load EDAM tabular data at [{path}] path does not exist."
        handle = io.open(path, "r")
    else:
        assert tabular_stream is not None, "Failed to load optional import from edam-onotology package, install using [pip install edam-ontology]."
        handle = tabular_stream()
    return load_edam_tree_from_tsv_stream(handle)


def load_edam_tree_from_tsv_stream(tsv_stream: TextIO):
    edam: Dict[str, Dict] = {}

    def _recurse_edam_parents(term, path=None):
        if edam[term]['parents'] and len(edam[term]['parents']) > 0:
            for parent in edam[term]['parents']:
                yield from _recurse_edam_parents(parent, path + [parent])
        else:
            yield path

    for line in tsv_stream.readlines():
        fields = line.split('\t')

        term = fields[COLUMN_TERM]
        if not term.startswith(EDAM_PREFIX):
            continue

        term_id = term[len(EDAM_PREFIX):]

        # Only care about formats and operations
        if not (term_id.startswith('operation_') or term_id.startswith('topic_')):
            continue

        parents = fields[COLUMN_PARENTS].split('|')
        edam[term_id] = {
            'label': fields[COLUMN_LABEL],  # preferred label
            'parents': [x[len(EDAM_PREFIX):] for x in parents if x.startswith(EDAM_PREFIX)],
        }

    for term in sorted(edam.keys()):
        tails = []
        for x in _recurse_edam_parents(term, path=[]):
            if x[-2:] not in tails:
                tails.append(x[-2:])
        edam[term]['path'] = tails

    return edam


__all__ = ('load_edam_tree', 'ROOT_OPERATION', 'ROOT_TOPIC')
