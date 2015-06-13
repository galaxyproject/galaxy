#!/usr/bin/env python

import sys;
import os;
import json;
import csv;

def create_json_line_for_output_dataset(json_file_fptr, name, ext, id, output_dataset_file, file_size=None, stdout=None):
    
    if(file_size == None):
        #filename = 'galaxy_dataset_%s.dat'%dataset_assoc_id;
        filename = output_dataset_file;
        if(os.path.exists(filename)):
            file_size = '%d'%int(os.path.getsize(filename));
        else:
            file_size = '4096'; #arbitrary size

    if(stdout == None):
        stdout = 'Remote dataset';

    line_dict = dict();
    line_dict['name'] = name;
    line_dict['stdout'] = stdout;
    line_dict['ext'] = ext;
    line_dict['remote_dataset'] = True;
    line_dict['dataset_id'] = int(id);
    line_dict['type'] = 'dataset';
    line_dict['file_size'] = file_size;

    json.dump(line_dict, json_file_fptr);
    json_file_fptr.write('\n');

def create_json_file(argv):
    json_file = argv[0];
    if(os.path.exists(json_file)):      #Tool created json file exists, don't bother to overwrite
        return;
    json_file_fptr = open(json_file, 'w');
    field_name_to_idx = { 'name':0, 'ext':1, 'id':2, 'output_dataset_file':3, 'file_size':4, 'stdout':5 }; 
    arg_idx = 1;
    for tokens in csv.reader(argv[arg_idx:], delimiter=':'):
        if(len(tokens) < 4):
            sys.stderr.write('Output dataset descriptor requires 4 fields <name>:<ext>:<dataset_id>:<output_dataset_file> [ <file_size> <stdout_string> ]\n');
            sys.stderr.write('Output dataset descriptor seems malformed: '+argv[arg_idx]+'\n');
            json_file_fptr.close();
            sys.exit(-1);
        name = tokens[field_name_to_idx['name']];
        ext = tokens[field_name_to_idx['ext']];
        id = tokens[field_name_to_idx['id']];
        output_dataset_file = tokens[field_name_to_idx['output_dataset_file']];
        file_size = tokens[field_name_to_idx['file_size']] if ( len(tokens) > field_name_to_idx['file_size'] ) else None;
        stdout = tokens[field_name_to_idx['stdout']] if ( len(tokens) > field_name_to_idx['stdout'] ) else None;
        #Create line in the JSON file
        create_json_line_for_output_dataset(json_file_fptr, name=name, ext=ext, id=id, output_dataset_file=output_dataset_file,
	    file_size=file_size, stdout=stdout);
        arg_idx += 1;

    json_file_fptr.close();

#Arguments to the script are:
#JSON file to be created
#A list of output dataset descriptors of the form: "name":ext:id:"file_path"  "name":ext:id:"file_path" "name":ext:id:"file_path"
#One tuple for each output dataset
if __name__ == "__main__":
    if(len(sys.argv) < 3):
        sys.stderr.write('Needs at least 2 arguments: <json_file_path> <output_dataset_descriptor>\n');
        sys.exit(-1);
    create_json_file(sys.argv[1:]);

