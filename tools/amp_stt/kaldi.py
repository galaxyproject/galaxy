#!/usr/bin/env python3

import os.path
import shutil
import subprocess
import sys
import tempfile

# The run_kaldi.sh script is assumed to be in a directory called kaldi-pua-singularity, which is a peer to the
# galaxy install.  It can either be a check out of that repo, or just the script and the appropriate .sif file.
# by default the cwd is somewhere near: 
#    galaxy/database/jobs_directory/000/4/working
MODE = "cpu"

def main():
    (root_dir, input_file, json_file, text_file) = sys.argv[1:5]
    print(os.getcwd())
    # copy the input file to a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copy(input_file, f"{tmpdir}/xxx.wav")
        
        script = mgm_utils.get_sif_dir(root_dir) + "/run_kaldi.sh"
        subprocess.run([script, MODE, tmpdir], check=True)
        # assuming the local kaldi ran, it's time to 
        # find our output files and copy them 
        print(os.listdir(tmpdir))
        print(os.listdir(f"{tmpdir}/transcripts/txt"))
        
        shutil.copy(f"{tmpdir}/transcripts/txt/xxx_16kHz.txt", text_file)
        shutil.copy(f"{tmpdir}/transcripts/json/xxx_16kHz.json", json_file)
        print(os.listdir(os.path.dirname(json_file)))
        print(os.listdir(os.path.dirname(text_file)))
    exit(0)

if __name__ == "__main__":
    main()
