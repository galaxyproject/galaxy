from galaxy import jobs

import operation_filter

def validate_input( trans, error_map, param_values, page_param_map ):
    operation_filter.validate_input( trans, error_map, param_values, page_param_map)

def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    operation_filter.exec_after_process(
        app, inp_data, out_data, param_dict, tool=tool, stdout=stdout, stderr=stderr)

    # strip strand column if clusters were merged
    if param_dict["returntype"] == '1':
        items = out_data.items()
        for name, data in items:
            data.metadata.strandCol = 0
