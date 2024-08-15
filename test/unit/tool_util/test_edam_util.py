import tempfile
from typing import (
    Any,
    Dict,
)

from edam_ontology.streams import tabular_stream

from galaxy.tool_util.edam_util import load_edam_tree


def test_load_edam_tree():
    tree = load_edam_tree()
    _verify_tree(tree)


def test_load_edam_tree_from_path():
    tf = tempfile.NamedTemporaryFile("w")
    tf.write(tabular_stream().read())
    tf.flush()
    tree = load_edam_tree(tf.name)
    _verify_tree(tree)


def _verify_tree(tree: Dict[str, Any]):
    assert tree is not None
    assert "operation_0004" in tree
    assert "topic_3974" in tree
    assert tree["topic_3974"]["label"] == "Epistasis"
    assert tree["topic_3974"]["parents"] == ["topic_0622", "topic_3295"]
    assert tree["topic_3974"]["path"] == [["topic_3391", "topic_0003"], ["topic_3070", "topic_0003"]]
    assert (
        tree["topic_3974"]["definition"]
        == "The study of the epigenetic modifications of a whole cell, tissue, organism etc."
    )
