#!/usr/bin/env python 
import sys
import os
import subprocess
import tempfile
import argparse
import shutil

def cleanup_files(*files):
    for file in files:
        if(os.path.exists(file)):
            os.remove(file);

def check_and_get_file_from_env_var(file_env_var):
    file_path=os.environ.get(file_env_var, None);
    if(not file_path):
        sys.stderr.write('Environment variable '+file_env_var+' not set - exiting\n');
        sys.exit(-1);
    if(not os.path.exists(file_path)):
        sys.stderr.write('Could not access file specified by environment variable '+file_env_var+' = '+file_path+' - exiting\n');
        sys.exit(-1);
    return file_path;

bcftools = check_and_get_file_from_env_var('BCFTOOLS');
tiledb_import_exe = check_and_get_file_from_env_var('TILEDB_IMPORT_EXE');
gcc49_prefix_path = check_and_get_file_from_env_var('GCC49_PREFIX_PATH');

ld_library_path = os.environ.get('LD_LIBRARY_PATH','');
os.environ['LD_LIBRARY_PATH'] = gcc49_prefix_path+'/lib64:'+gcc49_prefix_path+'/lib:'+ld_library_path

parser = argparse.ArgumentParser();
parser.add_argument('vcf_files', nargs='+', help='list of vcf/bcf files');
parser.add_argument('--tiledb_name', help='Name of TileDB database', default='GT');
parser.add_argument('--info_file', help='File where this tool prints some info', default=None);
args=parser.parse_args();

cwd=os.getcwd();

#Combined csv file created for import into TileDB
try:
    csv_fd,csv_filename = tempfile.mkstemp(dir=cwd);
    os.close(csv_fd);
except:
    sys.stderr.write('Unexpected error while creating csv file '+str(sys.exc_info()[0]));
    cleanup_files(csv_filename);
    raise
#Scratch sqlite file - created in /tmp space to avoid file locaking issues
try:
    sqlite_fd,sqlite_filename = tempfile.mkstemp(suffix='.sqlite', dir='/tmp');
    os.close(sqlite_fd);
except:
    sys.stderr.write('Unexpected error while creating sqlite file '+str(sys.exc_info()[0]));
    cleanup_files(sqlite_filename, csv_filename);
    raise
sqlite_create_commands=[
        'CREATE TABLE contig_names ( contig_name VARCHAR(250) UNIQUE on conflict fail, contig_idx INTEGER PRIMARY KEY, contig_length bigint, contig_offset bigint UNIQUE on conflict fail);',
        'CREATE TABLE field_names ( field_name VARCHAR(250) UNIQUE on conflict fail, field_idx INTEGER PRIMARY KEY);',
        'CREATE TABLE sample_names ( sample_name VARCHAR(250) UNIQUE on conflict fail, sample_idx INTEGER PRIMARY KEY);',
        ];

try:
    subprocess.check_call('sqlite3 '+sqlite_filename+' \''+''.join(sqlite_create_commands)+'\'', shell=True);
except subprocess.CalledProcessError:
    sys.stderr.write('Unexpected error while creating tables in sqlite file '+str(sys.exc_info()[0]));
    cleanup_files(sqlite_filename, csv_filename);
    raise

for vcf_file in args.vcf_files:
    try:
        subprocess.check_call(bcftools+' view -O t --sqlite='+sqlite_filename+' '+vcf_file+' >> '+csv_filename, shell=True);
    except subprocess.CalledProcessError:
        sys.stderr.write('Unexpected error while importing VCF/BCF file '+vcf_file+' : '+str(sys.exc_info()[0]));
        cleanup_files(sqlite_filename, csv_filename);
        raise

num_samples = len(args.vcf_files);
workspace = tempfile.mkdtemp(dir=cwd);
tmpdir = workspace+'/tmp';
os.mkdir(tmpdir);
try:
    subprocess.check_call((tiledb_import_exe+' -w '+workspace+' -A '+args.tiledb_name+' -f '+csv_filename+' -N %d --temp-space='+tmpdir)%(num_samples), shell=True);
except subprocess.CalledProcessError:
    sys.stderr.write('Unexpected error while importing into TileDB '+str(sys.exc_info()[0]));
    cleanup_files(sqlite_filename, csv_filename);
    shutil.rmtree(workspace);
    raise

info_string=('INFO: imported variants from %d VCF/BCF file(s) into TileDB instance '+args.tiledb_name)%(num_samples);
print(info_string);

if(args.info_file):
    fptr=open(args.info_file, 'wb');
    fptr.write(info_string+'\n');
    fptr.close();

cleanup_files(sqlite_filename, csv_filename);
shutil.rmtree(workspace);
