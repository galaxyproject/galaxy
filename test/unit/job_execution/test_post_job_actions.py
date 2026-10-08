from unittest.mock import Mock

import pytest

from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.job_execution.actions.post import (
    ChangeDatatypeAction,
    RenameDatasetAction,
)
from galaxy.model import (
    Job,
    PostJobAction,
)
from galaxy.util.bunch import Bunch


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


@pytest.mark.parametrize(
    "current,newtype,expected",
    [
        ("tabular", "txt", "txt"),
        ("fastqsanger.c4gh", "c4gh", "c4gh"),
        ("fastqsanger.c4gh", "tabular", "tabular.c4gh"),
        ("fastqsanger.c4gh", "tabular.c4gh", "tabular.c4gh"),
        ("fastqsanger.c4gh", "not_a_datatype", "fastqsanger.c4gh"),
        ("tabular", "tabular.c4gh", "tabular"),
    ],
)
def test_change_datatype_keeps_encryption(current, newtype, expected):
    registry = example_datatype_registry_for_sample(crypt4gh_enabled=True)
    dataset = Mock(extension=current, datatype=registry.get_datatype_by_extension(current))
    dataset.has_data.return_value = False
    job = Bunch(state=Job.states.OK, states=Job.states, output_datasets=[Bunch(name="out_file1", dataset=dataset)])
    action = PostJobAction("ChangeDatatypeAction", output_name="out_file1", action_arguments={"newtype": newtype})
    ChangeDatatypeAction.execute(Bunch(datatypes_registry=registry), None, action, job)
    assert dataset.extension == expected
