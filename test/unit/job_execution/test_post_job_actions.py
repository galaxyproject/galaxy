import pytest

from galaxy.job_execution.actions.post import RenameDatasetAction
from galaxy.model import PostJobAction


@pytest.mark.parametrize(
    "template,input_names,expected",
    [
        ("#{input1}", {"cond|xinput1": "wrong", "cond|input1": "right"}, "right"),
        ("#{s}", {"main|barcodes": "wrong", "main|s": "right"}, "right"),
        ("Renamed #{input1}", {"cond|xinput1": "wrong"}, "Renamed "),
        ("#{input}", {"cond|other_input": "wrong", "repeat_0|nested|input": "right"}, "right"),
        ("#{input}", {"cond|input": "first", "other|input": "second"}, "first"),
        ("#{input}", {"cond|input": "nested", "input": "top level"}, "top level"),
        ("#{cond.input}", {"other|input": "wrong", "cond|input": "right"}, "right"),
        ("#{cond.input}", {"outer|xcond|input": "wrong", "outer|cond|input": "right"}, "right"),
        ("#{queries_0.input2 | basename | upper}", {"queries_0|input2": "reads.fastq"}, "READS"),
        ("Renamed #{missing}", {"cond|input": "unused"}, "Renamed "),
    ],
)
def test_rename_input_references(template, input_names, expected):
    action = PostJobAction("RenameDatasetAction", action_arguments={"newname": template})
    assert RenameDatasetAction._gen_new_name(action, input_names, {}) == expected
