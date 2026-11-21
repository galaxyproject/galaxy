import os

import pytest

from galaxy.app_unittest_utils.tools_support import UsesTools

LEGACY_TOOL_CONTENTS = """<tool id="${tool_id}" name="Legacy Tool" version="$version">
    <command>python '$__tool_directory__/${main_script}' '$input1' '$out_file1'</command>
    <inputs>
        <param type="data" format="txt" name="input1" />
    </inputs>
    <outputs>
        <data name="out_file1" format="txt" />
    </outputs>
</tool>
"""

# Script layouts of the Tool Shed repository revisions these tools ship in.
LEGACY_TOOL_LAYOUTS = [
    ("fasta_compute_length", "1.0.3", "fasta_compute_length.py", ["utils/__init__.py", "utils/fasta_to_len.py"]),
    ("fasta_concatenate0", "0.0.1", "fasta_concatenate_by_species.py", ["utils/__init__.py", "utils/maf_utilities.py"]),
    ("flanking_features_1", "4.0.1", "flanking_features.py", ["utils/__init__.py", "utils/gff_util.py"]),
    ("gops_intersect_1", "1.0.0", "gops_intersect.py", ["utils/__init__.py", "utils/gff_util.py"]),
    ("gops_subtract_1", "1.0.0", "gops_subtract.py", ["utils/__init__.py", "utils/gff_util.py"]),
    ("translate_bed", "0.1.0", "translate_bed.py", ["bedutil.py", "digest.py", "ensembl_rest.py"]),
]


class TestImplicitlyRequiredToolFiles(UsesTools):
    def setup_method(self):
        self.setup_app()

    def teardown_method(self):
        self.tear_down_app()

    @pytest.mark.parametrize("tool_id,version,main_script,support_files", LEGACY_TOOL_LAYOUTS)
    def test_main_script_is_required(self, tool_id, version, main_script, support_files):
        for rel_path in [main_script, *support_files, "test-data/input.fa"]:
            path = os.path.join(self.test_directory, rel_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("")
        tool = self._init_tool(
            LEGACY_TOOL_CONTENTS.replace("${main_script}", main_script), tool_id=tool_id, version=version
        )

        assert tool.required_files is not None
        required = tool.required_files.find_required_files(tool.tool_dir)
        assert sorted(required) == sorted([main_script, *support_files])
