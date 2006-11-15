#build list of available data
import sys
builds= []

try:
    #read db names from file, this file is also used in galaxy/util.py
    for line in open("static/ucsc/builds.txt"):
        if line[0:1] == "#": continue
        try:
            fields = line.replace("\r","").replace("\n","").split("\t")
            builds.append((fields[1], fields[0], False))
        except: continue
except Exception, exc:
    print >>sys.stdout, 'axt_to_fasta_code.py initialization error -> %s' % exc 

#return available builds
def get_available_builds():
    try:
        available_options = builds[0:]
    except:
        available_options = []
    if len(available_options) < 1:
        available_options.append(('unspecified','?',True))
    return available_options
