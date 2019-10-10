#!/usr/bin/env python3

import os
import subprocess
import sys


def main():
	(input_file, json_file) = sys.argv[1:3]
	
	r = subprocess.run(["/srv/amp/ina-speech-tools-singularity/ina-speech-tools-singularity.sif", input_file, json_file])
	
	exit(r.returncode)
		
if __name__ == "__main__":
	main()
