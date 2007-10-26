
def exec_before_job(app, inp_data, out_data, param_dict, tool):
    maf_sets = {}
    if param_dict['maf_source_type']['maf_source'] == "cached":
        for name, data in out_data.items():
            try:
                data.name = data.name + " [" + maf_sets[str(param_dict['maf_source_type']['mafType'])]['description'] + "]"
            except KeyError:
                data.name = data.name + " [unknown MAF source specified]"
    if param_dict['summary'].lower() == "true":
        for name, data in out_data.items():
            data.change_datatype('tabular')
