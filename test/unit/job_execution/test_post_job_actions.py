import pytest

from galaxy.job_execution.actions.post import RenameDatasetAction
from galaxy.model import PostJobAction


@pytest.mark.parametrize(
    "template,input_names,expected",
    [
        ("#{input1}", {"cond|xinput1": "wrong", "cond|input1": "right"}, "right"),
        ("#{s}", {"main|barcodes": "wrong", "main|s": "right"}, "right"),
        ("#{e}", {"mode_conditional|reference": "wrong", "mode_conditional|advanced_options|e": "right"}, "right"),
        (
            "#{file}",
            {"rep_experiment_0|chrom_len_file": "wrong", "rep_experiment_0|rep_samples_0|file": "right"},
            "right",
        ),
        (
            "#{intervals}",
            {"optional|excl_ival_type|exclude_intervals": "wrong", "optional|ival_type|intervals": "right"},
            "right",
        ),
        ("Renamed #{input1}", {"cond|xinput1": "wrong"}, "Renamed "),
        ("#{input}", {"cond|other_input": "wrong", "repeat_0|nested|input": "right"}, "right"),
        ("#{input}", {"cond|input": "first", "other|input": "second"}, "first"),
        ("#{input}", {"cond|input": "nested", "input": "top level"}, "top level"),
        ("#{cond.input}", {"other|input": "wrong", "cond|input": "right"}, "right"),
        ("#{cond.input}", {"outer|xcond|input": "wrong", "outer|cond|input": "right"}, "right"),
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
        ("#{a#{b}}", {"a": "x", "b": "y"}, "}"),
    ],
)
def test_rename_input_references(template, input_names, expected):
    action = PostJobAction("RenameDatasetAction", action_arguments={"newname": template})
    assert RenameDatasetAction._gen_new_name(action, input_names, {}) == expected
