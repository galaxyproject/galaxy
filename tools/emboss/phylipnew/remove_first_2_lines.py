#removes first 2 lines from all outputfiles

import operator
import os
from galaxy import datatypes


def exec_after_process(app, inp_data, out_data, param_dict,tool, stdout, stderr):
    for data_count in range(len(out_data)):
        output_filename = param_dict.get( 'out_file'+str(data_count+1), None )
        if output_filename != None:
            file = open(output_filename, 'r')
            contents = file.readlines()
            file.close()
            contents = contents[3:]
            file = open(output_filename, 'w')
            for line in contents:
                file.write(line)
            file.close()
