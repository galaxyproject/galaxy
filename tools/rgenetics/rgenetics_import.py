#!/usr/bin/env python2.4

"""
Creates an html file to be used for viewing rgenetics files

   <command interpreter="python2.4">rgenetics_import.py $file_type_dir $base_name $output </command>


"""

import sys, os, glob

galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" />
<title></title>
<link rel="stylesheet" href="/static/style/base.css" type="text/css" />
</head>
<body>
<div class="document">
"""

def doProjectImport():
    """ import into an html composite data type for Rgenetics
        Important metadata manipulations in an exec_after_process hook:
        
# Create links to files here - note number is not known initially
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    for i,data in out_data.values(): # may be many
        ftd = param_dict['file_type_dir'][i] 
        data.change_datatype(os.path.split(ftd)[-1])
        data.file_name = data.file_name
        basename = param_dict['base_name'][i]
        data.metadata.base_name = basename
        data.name = basename
        data.flush()
        data.dataset_file.extra_files_path = ftd
        data.dataset_file.readonly = True
        data.flush()
    app.model.flush()
        
        Dan Blankenberg with mods by Ross Lazarus 
        October 2007
    """
    progname = sys.argv[0]
    file_type_dirs = sys.argv.pop(1).strip().split(',')
    base_names = sys.argv.pop(1).strip().split(',')
    output = sys.argv.pop(1)
    out = open(output,'w')
    out.write(galhtmlprefix % progname)
    for n,file_type_dir in enumerate(file_type_dirs):
        basename = base_names[n]
        flist = glob.glob("%s.*" % os.path.join(file_type_dir, basename))
        for i, data in enumerate( flist ):
            out.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    out.write("</div></body></html>")
    out.close()



def doImport():
    """ import into one of the new html composite data types for Rgenetics
        Important metadata manipulations in an exec_after_process hook:
        
# Create link to files here
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    data = out_data.values()[0]
    data.change_datatype(os.path.split(param_dict['file_type_dir'])[-1])
    data.file_name = data.file_name
    base_name = param_dict['base_name']
    data.metadata.base_name = base_name
    data.name = base_name
    data.flush()
    data.dataset_file.extra_files_path = param_dict['file_type_dir']
    data.dataset_file.readonly = True
    data.flush()
    app.model.flush()
        
        Dan Blankenberg with mods by Ross Lazarus 
        October 2007
    """
    progname = sys.argv[0]
    file_type_dir = sys.argv.pop(1)
    base_name = sys.argv.pop(1)
    output = sys.argv.pop(1)
    out = open(output,'w')
    out.write(galhtmlprefix % progname)
    flist = glob.glob("%s.*" % os.path.join(file_type_dir, base_name))
    for i, data in enumerate( flist ):
        print 'writing data %s' % data
        out.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    out.write("</div></body></html>")
    out.close()


if __name__ == "__main__": 
   doImport()

