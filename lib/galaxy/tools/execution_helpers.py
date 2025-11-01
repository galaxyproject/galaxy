"""Helpers meant to assist tool execution.

Lower-level things that prevent interwoven dependencies between tool code,
tool execution code, and tool action code.
"""

import logging
from typing import Optional

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


def on_text_for_names(names: Optional[list[str]], prefix: Optional[str] = None) -> str:
    if names is None or len(names) == 0:
        return ""

    # Build name for output datasets based on tool name and input names
    on_text = ""
    if len(names) == 1:
        on_text = f"{names[0]}"
    elif len(names) == 2:
        on_text = f"{names[0]} and {names[1]}"
    elif len(names) == 3:
        on_text = f"{names[0]}, {names[1]}, and {names[2]}"
    else:
        on_text = f"{names[0]}, {names[1]}, and others"

    if prefix:
        on_text = f"{prefix} {on_text}"

    return on_text


def on_text_for_numeric_ids(ids: Optional[list[int]], prefix: Optional[str] = None) -> str:
    if ids is None or len(ids) == 0:
        return ""
    # ids may contain duplicates... this is because the first value in
    # multiple input dataset parameters will appear twice once as param_name
    # and once as param_name1.
    groups = []
    unique_ids = sorted(set(ids))
    for group_it in consecutive_groups(unique_ids):
        group = list(group_it)
        if len(group) == 1:
            groups.append(str(group[0]))
        elif len(group) == 2:
            groups.extend([str(group[0]), str(group[1])])
        else:
            groups.append(f"{group[0]}-{group[-1]}")

    return on_text_for_names(groups, prefix)


def on_text_for_dataset_and_collections(
    dataset_hids: Optional[list[int]] = None,
    collection_hids: Optional[list[int]] = None,
    element_ids: Optional[list[str]] = None,
) -> str:
    on_text_datasets = on_text_for_numeric_ids(dataset_hids, "dataset")
    on_text_collection = on_text_for_numeric_ids(collection_hids, "collection")
    on_text_elements = on_text_for_names(element_ids)

    on_text = []
    if on_text_datasets:
        on_text.append(on_text_datasets)
    if on_text_collection:
        on_text.append(on_text_collection)
    if on_text_elements:
        on_text.append(on_text_elements)

    if len(on_text) == 0:
        return ""
    elif len(on_text) == 1:
        return on_text[0]
    else:
        return ", ".join(on_text[:-1]) + " and " + on_text[-1]
