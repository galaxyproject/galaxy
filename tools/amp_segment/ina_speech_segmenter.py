#!/usr/bin/env python3

import os
import os.path
import shutil
import subprocess
import sys
import tempfile
import uuid

import mgm_utils

def main():
	(root_dir, input_file, json_file) = sys.argv[1:4]
	tmpName = str(uuid.uuid4())
	tmpdir = "/tmp"
	temp_input_file = f"{tmpdir}/{tmpName}.dat"
	temp_output_file = f"{tmpdir}/{tmpName}.json"
	shutil.copy(input_file, temp_input_file)

	sif = mgm_utils.get_sif_dir(root_dir) + "/ina_segmentation.sif"
	r = subprocess.run(["singularity", "run", sif, temp_input_file, temp_output_file])
	
	shutil.copy(temp_output_file, json_file)

	if os.path.exists(temp_input_file):
		os.remove(temp_input_file)

	if os.path.exists(temp_output_file):
		os.remove(temp_output_file)
		
	exit(r.returncode)
		
if __name__ == "__main__":
	main()
