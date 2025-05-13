"""Helpers meant to assist tool execution.

Lower-level things that prevent interwoven dependencies between tool code,
tool execution code, and tool action code.
"""

import logging
from typing import (
    Collection,
    Optional,
)

from more_itertools import consecutive_groups

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


def on_text_for_names(hids: Optional[Collection[int]], prefix: str) -> str:
    if hids is None or len(hids) == 0:
        return ""
    # hids may contain duplicates... this is because the first value in
    # multiple input dataset parameters will appear twice once as param_name
    # and once as param_name1.
    groups = []
    unique_hids = sorted(set(hids))
    for group in consecutive_groups(unique_hids):
        group = list(group)
        if len(group) == 1:
            groups.append(str(group[0]))
        elif len(group) == 2:
            groups.extend([str(group[0]), str(group[1])])
        else:
            groups.append(f"{group[0]}-{group[-1]}")

    # Build name for output datasets based on tool name and input names
    on_text = ""
    if len(groups) == 1:
        on_text = f"{prefix} {groups[0]}"
    elif len(groups) == 2:
        on_text = f"{prefix} {groups[0]} and {groups[1]}"
    elif len(groups) == 3:
        on_text = f"{prefix} {groups[0]}, {groups[1]}, and {groups[2]}"
    else:
        on_text = f"{prefix} {groups[0]}, {groups[1]}, and others"
    return on_text


def on_text_for_dataset_and_collections(
    dataset_hids: Optional[Collection[int]] = None, collection_hids: Optional[Collection[int]] = None
) -> str:
    on_text_datasets = on_text_for_names(dataset_hids, "data")
    on_text_collection = on_text_for_names(collection_hids, "list")
    on_text = []
    if on_text_datasets:
        on_text.append(on_text_datasets)
    if on_text_collection:
        on_text.append(on_text_collection)
    if len(on_text) == 0:
        return ""
    elif len(on_text) == 1:
        return on_text[0]
    else:
        return on_text[0] + " and " + on_text[1]
