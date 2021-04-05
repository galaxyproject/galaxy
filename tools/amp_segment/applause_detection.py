#!/usr/bin/env python3

import os
import os.path
import shutil
import subprocess
import sys
import tempfile

# The applause_detection singularity file is assumed to be at /srv/amp/applause_detection/applause_detection.sif
APPLAUSE_DETECTION = "/srv/amp/applause-detection/applause-detection.sif"

def main():
    (input_audio, min_segment_duration, amp_segments) = sys.argv[1:4]
    print("Current directory: " + os.getcwd())
    print("Input audio: " + input_audio)
    
    # use a tmp directory accessible to the singularity for input/output
    with tempfile.TemporaryDirectory() as tmpdir:
        # copy the input audio file to the tmp directory
        filename = os.path.basename(input_audio)
        shutil.copy(input_audio, f"{tmpdir}/{filename}")
        print("Temporary directory " + tmpdir + " after input file copied: " + str(os.listdir(tmpdir)))
        
        # run singularity
        subprocess.run([APPLAUSE_DETECTION, tmpdir, min_segment_duration], check=True)

        # copy the corresponding temporary output file to the output AMP segments JSON
        print("Temporary directory " + tmpdir + " after output file generated: " + str(os.listdir(tmpdir)))   
        shutil.copy(f"{tmpdir}/{filename}.json", amp_segments)
        print("Output AMP Segment: " + amp_segments)
    exit(0)

if __name__ == "__main__":
    main()
