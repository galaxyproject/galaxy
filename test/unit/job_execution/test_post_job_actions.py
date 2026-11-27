import pytest

from galaxy.job_execution.actions.post import RenameDatasetAction
from galaxy.model import PostJobAction


@pytest.mark.parametrize(
    "template,input_names,expected",
    [
        ("#{input}", {"cond|input": "first", "other|input": "second"}, "first"),
        ("#{input}", {"cond|input": "nested", "input": "top level"}, "top level"),
        ("#{cond.input}", {"other|input": "wrong", "cond|input": "right"}, "right"),
        ("#{queries_0.input2 | basename | upper}", {"queries_0|input2": "reads.fastq"}, "READS"),
        ("Renamed #{missing}", {"cond|input": "unused"}, "Renamed "),
        ("#{missing}#{input} suffix", {"input": "reads.fastq"}, "reads.fastq suffix"),
        ("#{missing}_#{input}", {"input": "reads.fastq"}, "_reads.fastq"),
        ("#{a}-#{b}", {"a": "", "b": "y"}, "-y"),
        ("#{a}#{b}", {"a": "x", "b": "longer"}, "xlonger"),
        ("#{a}#{b}#{c}", {"a": "", "b": "", "c": "z"}, "z"),
        ("#{input}#{missing} suffix", {"input": "reads.fastq"}, "reads.fastq suffix"),
        ("#{a}_#{a}", {"a": "x"}, "x_x"),
        ("#{a} x", {"a": "ab#{b}", "b": "other"}, "ab#{b} x"),
        ("#{a} #{b}", {"a": "#{b}", "b": "B"}, "#{b} B"),
        ("pre #{a", {"a": "x"}, "pre #{a"),
        ("#{a} and #{b", {"a": "x"}, "x and #{b"),
        # A reference runs from #{ to the first }, so "a#{b" is looked up and the trailing } is kept.
        ("#{a#{b}}", {"a": "x", "b": "y"}, "}"),
        ("#{ a | upper }", {"a": "x"}, "X"),
        # Names are only stripped when operations follow.
        ("#{ a }", {"a": "x"}, ""),
        ("#{}#{a}", {"a": "x"}, "x"),
    ],
)
def test_rename_input_references(template, input_names, expected):
    action = PostJobAction("RenameDatasetAction", action_arguments={"newname": template})
    assert RenameDatasetAction._gen_new_name(action, input_names, {}) == expected


def test_rename_applies_replacement_dict_after_input_references():
    action = PostJobAction("RenameDatasetAction", action_arguments={"newname": "#{a} ${sample}"})
    assert RenameDatasetAction._gen_new_name(action, {"a": "reads"}, {"sample": "S1"}) == "reads S1"
