"""Helpers meant to assist tool execution.

Lower-level things that prevent interwoven dependencies between tool code,
tool execution code, and tool action code.
"""

import logging
from typing import (
    Collection,
    Optional,
)

log = logging.getLogger(__name__)


class ToolExecutionCache:
    """An object meant to cache calculation caused by repeatedly evaluting
    the same tool by the same user with slightly different parameters.
    """

    def __init__(self, trans):
        self.trans = trans
        self.current_user_roles = trans.get_current_user_roles()
        self.chrom_info = {}
        self.cached_collection_elements = {}

    def get_chrom_info(self, tool_id, input_dbkey):
        genome_builds = self.trans.app.genome_builds
        custom_build_hack_get_len_from_fasta_conversion = tool_id != "CONVERTER_fasta_to_len"
        if custom_build_hack_get_len_from_fasta_conversion and input_dbkey in self.chrom_info:
            return self.chrom_info[input_dbkey]

        chrom_info_pair = genome_builds.get_chrom_info(
            input_dbkey,
            trans=self.trans,
            custom_build_hack_get_len_from_fasta_conversion=custom_build_hack_get_len_from_fasta_conversion,
        )
        if custom_build_hack_get_len_from_fasta_conversion:
            self.chrom_info[input_dbkey] = chrom_info_pair

        return chrom_info_pair


def filter_output(tool, output, incoming):
    for filter in output.filters:
        try:
            if not eval(filter.text.strip(), globals(), incoming):
                return True  # do not create this dataset
        except Exception as e:
            log.debug(f"Tool {tool.id} output {output.name}: dataset output filter ({filter.text}) failed: {e}")
    return False


def on_text_for_names(input_names: Optional[Collection[str]], prefix) -> str:
    if input_names is None:
        return ""
    # input_names may contain duplicates... this is because the first value in
    # multiple input dataset parameters will appear twice once as param_name
    # and once as param_name1.
    unique_names = []
    for name in input_names:
        if name not in unique_names:
            unique_names.append(name)
    input_names = unique_names

    # Build name for output datasets based on tool name and input names
    if len(input_names) == 0:
        on_text = ""
    elif len(input_names) == 1:
        on_text = prefix + " " + input_names[0]
    elif len(input_names) == 2:
        on_text = prefix + "s {} and {}".format(*input_names)
    elif len(input_names) == 3:
        on_text = prefix + "s {}, {}, and {}".format(*input_names)
    else:
        on_text = prefix + "s {}, {}, and others".format(*input_names[:2])
    return on_text


def on_text_for_dataset_and_collections(
    dataset_names: Optional[Collection[str]] = None, collection_names: Optional[Collection[str]] = None
) -> str:
    return on_text_for_names(collection_names, "collection") + on_text_for_names(dataset_names, "dataset")
