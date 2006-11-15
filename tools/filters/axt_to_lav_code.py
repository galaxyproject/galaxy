#build list of available data
import sys
builds= []

try:
    #read db names from file, this file is also used in galaxy/util.py
    for line in open("static/ucsc/builds.txt"):
        if line[0:1] == "#": continue
        try:
            fields = line.replace("\r","").replace("\n","").split("\t")
            if fields[0]=="?": continue
            builds.append((fields[1], fields[0], False))
        except: continue
except Exception, exc:
    print >>sys.stdout, 'axt_to_lav_code.py initialization error -> %s' % exc 

#return available builds
def get_available_builds(build="?"):
    if build != "?": return [('A valid build is already specified ('+build+')',build,True)]
    try:
        available_options = builds[0:]
    except:
        available_options = []
    if len(available_options) < 1:
        available_options.append(('unspecified','?',True))
    return available_options

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    for name,data in out_data.items():
        if name == "seq_file2":
            data.dbkey = param_dict['dbkey_2']
            data.flush()
            break