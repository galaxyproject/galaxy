#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import filecmp
import os
import pytest
import tempfile

from claragenomics.wrappers import wrappers
from claragenomics.utilities import utilities

# ground-truth files
current_dir = os.path.dirname(os.path.realpath(__file__))
reads_filepath = os.path.join(current_dir, "data/reads.fasta")
reference_filepath = os.path.join(current_dir, "data/ref.fasta")
overlaps_gt_filepath = os.path.join(current_dir, "data/overlaps_GT.paf")
assembly_gfa_gt_filepath = os.path.join(current_dir, "data/assembly_GT.gfa")
assembly_fa_gt_filepath = os.path.join(current_dir, "data/assembly_GT.fa")
overlaps_on_assembly_gt_filepath = os.path.join(current_dir, "data/overlaps_on_assembly_GT.paf")
polished_assembly_CPU_subgraph_gt_filepath = os.path.join(current_dir, "data/polished_assembly_CPU_subgraph_GT.fa")
report_CPU_subgraph_gt_filepath = os.path.join(current_dir, "data/polished_assembly_CPU_subgraph_GT.txt")


@pytest.mark.cpu
@pytest.mark.parametrize(
    "reads_filepath, overlaps_gt_filepath, minimap2_tool_path",
    [(reads_filepath, overlaps_gt_filepath, None)],
)
def test_minimap2_from_reads(reads_filepath, overlaps_gt_filepath, minimap2_tool_path):
    with tempfile.TemporaryDirectory(dir=".") as output_dir:
        # get overlap from read
        minimap2 = wrappers.Minimap2Wrapper(minimap2_tool_path)
        output_overlaps = os.path.join(output_dir, "tmp_overlaps.paf")
        minimap2.overlap(reads_filepath, reads_filepath, output_overlaps, args="-x ava-ont", extra_args="-t 12")
        # verify output is the same as ground-truth
        match = filecmp.cmp(output_overlaps, overlaps_gt_filepath)
        assert(match)


@pytest.mark.cpu
@pytest.mark.parametrize(
    "reads_filepath, assembly_fa_gt_filepath, minimap2_tool_path",
    [(reads_filepath, assembly_fa_gt_filepath, None)],
)
def test_minimap2_from_assembly(reads_filepath, assembly_fa_gt_filepath, minimap2_tool_path):
    with tempfile.TemporaryDirectory(dir=".") as output_dir:
        # map reads to assembly
        minimap2 = wrappers.Minimap2Wrapper(minimap2_tool_path)
        output_overlaps_on_assembly = os.path.join(output_dir, "tmp_overlaps_on_assembly.paf")
        minimap2.overlap(assembly_fa_gt_filepath, reads_filepath, output_overlaps_on_assembly)
        # verify output is the same as ground-truth
        match = filecmp.cmp(output_overlaps_on_assembly, overlaps_on_assembly_gt_filepath)
        assert(match)


@pytest.mark.cpu
@pytest.mark.parametrize(
    "reads_filepath, overlaps_gt_filepath, assembly_gfa_gt_filepath, miniasm_tool_path",
    [(reads_filepath, overlaps_gt_filepath, assembly_gfa_gt_filepath, None)],
)
def test_miniasm(reads_filepath, overlaps_gt_filepath, assembly_gfa_gt_filepath, miniasm_tool_path):
    with tempfile.TemporaryDirectory(dir=".") as output_dir:
        # get assemble from read
        miniasm = wrappers.MiniasmWrapper(miniasm_tool_path)
        output_assembly_gfa = os.path.join(output_dir, "tmp_assembly.gfa")
        miniasm.assemble(reads_filepath, overlaps_gt_filepath, output_assembly_gfa)
        # verify output is the same as ground-truth
        match = filecmp.cmp(output_assembly_gfa, assembly_gfa_gt_filepath)
        assert(match)


@pytest.mark.cpu
@pytest.mark.parametrize(
    "assembly_gfa_gt_filepath, assembly_fa_gt_filepath",
    [(assembly_gfa_gt_filepath, assembly_fa_gt_filepath)],
)
def test_gfa2fa(assembly_gfa_gt_filepath, assembly_fa_gt_filepath):
    with tempfile.TemporaryDirectory(dir=".") as output_dir:
        # convert assembly from gfa to fa format
        output_assembly_fa = os.path.join(output_dir, "tmp_assembly.fa")
        utilities.Utilities.gfa2fa(assembly_gfa_gt_filepath, output_assembly_fa)
        # verify output is the same as ground-truth
        match = filecmp.cmp(output_assembly_fa, assembly_fa_gt_filepath)
        assert(match)


@pytest.mark.cpu
@pytest.mark.parametrize("reads_filepath, overlaps_on_assembly_gt_filepath, assembly_fa_gt_filepath, \
                         polished_assembly_CPU_subgraph_gt_filepath, racon_tool_path",
                         [(reads_filepath, overlaps_on_assembly_gt_filepath, assembly_fa_gt_filepath,
                           polished_assembly_CPU_subgraph_gt_filepath, None)],
                         )
def test_racon_cpu(reads_filepath, overlaps_on_assembly_gt_filepath, assembly_fa_gt_filepath,
                   polished_assembly_CPU_subgraph_gt_filepath, racon_tool_path):
    with tempfile.TemporaryDirectory(dir=".") as output_dir:
        # polish with racon
        racon = wrappers.RaconWrapper(racon_tool_path, gpu=False)
        output_polished = os.path.join(output_dir, "tmp_polished_assembly.fa")
        racon.polish(reads_filepath, overlaps_on_assembly_gt_filepath, assembly_fa_gt_filepath, output_polished)
        # verify output is the same as ground-truth
        match = filecmp.cmp(output_polished, polished_assembly_CPU_subgraph_gt_filepath)
        assert(match)


# @pytest.mark.parametrize(
#     "reference_filepath, polished_gt_filepath, report_gt_filepath",
#     [(reference_filepath, polished_assembly_CPU_subgraph_gt_filepath, report_CPU_subgraph_gt_filepath)],
# )
# def test_quast(reference_filepath, polished_gt_filepath, report_gt_filepath):
#     with tempfile.TemporaryDirectory(dir=".") as report_dir:
#         # evaluate assemble result
#         quast = wrappers.QuastWrapper()
#         quast.assess(polished_gt_filepath, reference_filepath, report_dir)

#         print("debugging CI!!!!!!!!!!!!!!")
#         print("check reference gt:",os.path.isfile(reference_filepath))
#         print("size is", os.path.getsize(reference_filepath))

#         print("check polished:",os.path.isfile(polished_gt_filepath))
#         print("size is", os.path.getsize(polished_gt_filepath))

#         print("check report gt:",os.path.isfile(report_gt_filepath))
#         print("size is", os.path.getsize(report_gt_filepath))
#         f = open(report_gt_filepath, 'r')
#         file_contents = f.read()
#         print(file_contents)
#         f.close()
#         tmp = os.path.join(report_dir,"report.txt")
#         print("check output report:", os.path.isfile(tmp))
#         print("size is", os.path.getsize(os.path.join(tmp)))
#         f = open(tmp, 'r')
#         file_contents = f.read()
#         print(file_contents)
#         f.close()

#         # cmd = "cat {}".format(output_assembly_fa)
#         # subprocess.call(cmd, shell=True)

#         # calculate error rate
#         error_gt = utilities.Utilities.calculate_error(report_gt_filepath)
#         error_predicted = utilities.Utilities.calculate_error(os.path.join(report_dir,"report.txt"))
#         # verify output is the same as ground-truth
#         assert(abs(error_gt - error_predicted) < 10**(-9))
