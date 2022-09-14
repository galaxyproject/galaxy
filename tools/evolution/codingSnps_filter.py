#!/usr/bin/env python

# runs after the job (and after the default post-filter)
from galaxy.tools.parameters import DataToolParameter


def validate_input(trans, error_map, param_values, page_param_map):
    dbkeys = set()
    data_param_names = set()
    data_params = 0
    for name, param in page_param_map.items():
        if isinstance(param, DataToolParameter):
            # for each dataset parameter
            if param_values.get(name, None) is not None:
                dbkeys.add(param_values[name].dbkey)
                data_params += 1
                # check meta data
                try:
                    param = param_values[name]
                    int(param.metadata.startCol)
                    int(param.metadata.endCol)
                    int(param.metadata.chromCol)
                    if param.metadata.strandCol is not None:
                        int(param.metadata.strandCol)
                except Exception:
                    error_msg = (
                        "The attributes of this dataset are not properly set. "
                        "Click the pencil icon in the history item to set the chrom, start, end and strand columns."
                    )
                    error_map[name] = error_msg
            data_param_names.add(name)
    if len(dbkeys) > 1:
        for name in data_param_names:
            error_map[name] = (
                "All datasets must belong to same genomic build, "
                "this dataset is linked to build '%s'" % param_values[name].dbkey
            )
    if data_params != len(data_param_names):
        for name in data_param_names:
            error_map[name] = "A dataset of the appropriate type is required"
