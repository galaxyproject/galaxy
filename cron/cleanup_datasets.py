#!/usr/bin/env python

#This script removes deleted dataset files.
#Takes 3 arguments:
#   1: database directory to clean
#   2: postgres database name
#   3 (optional): number of days to allow as a buffer, defaults to 2
#python cleanup_datasets.py /home/universe/server-home/wsgi-postgres/database/files/ galaxy_test 2

import sys, os, tempfile, time
try:
    database_dir = sys.argv[1]
    database_name = sys.argv[2]
    num_days = 2
    try:
        num_days = int(sys.argv[3])
    except:
        print "Using Default of 2 days buffer on delete"
except:
    print "Usage: python %s path_to_files:/home/universe/server-home/wsgi-postgres/database/files/ database_name:galaxy_test [num_days_buffer:2]" % sys.argv[0]
    sys.exit(0)
id_file = tempfile.NamedTemporaryFile('w')
id_filename = id_file.name
id_file.close()
ids = []

command = "psql -d %s -c \"select id from dataset;\" -o %s" % (database_name, id_filename)
print "Getting IDs:", command
id_file = os.popen(command)
id_file.close()
for line in open(id_filename,'r'):
    try:
        ids.append(int(line.strip()))
    except:
        print line.strip(),"is not a valid id, skipping."
os.unlink(id_filename)
if len(ids) < 1:
    print "Less than 1 IDs have been found! Deleting proccess has been canceled."
    sys.exit(0)
print "-----%i IDs Retrieved -----" % len(ids)
print "----- Checking database directory for deleted ids: %s -----" % database_dir
file_size = 0
num_delete = 0
for result in os.walk(database_dir):
    this_base_dir,sub_dirs,files = result
    for file in files:
        if file.startswith("dataset_") and file.endswith(".dat"):
            id = int(file.replace("dataset_","").replace(".dat",""))
            file_name = os.path.join(this_base_dir,file)
            if id not in ids:
                file_time = os.path.getctime(file_name)
                if time.time() > file_time + (num_days*60*60*24): #num_days (default=2) days buffer room
                    num_delete += 1
                    size = os.path.getsize(file_name)
                    file_size += size
                    os.unlink(file_name)
print file_size, "bytes"
print float(file_size) / 1024, "kilobytes"
print float(file_size) / 1024 / 1024, "Megabytes"
print float(file_size) / 1024 / 1024 / 1024, "Gigabytes"
print "%i files deleted" % num_delete

sys.exit(0)