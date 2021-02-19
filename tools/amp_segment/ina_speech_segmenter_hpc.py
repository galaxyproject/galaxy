#!/bin/env python3
import argparse
from datetime import datetime
import csv
from pathlib import Path
import json
import logging
import sys
import os
sys.path.insert(0, os.path.abspath('../../../../../tools/amp_util'))
import hpc_submit
import mgm_utils
sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from segmentation import Segmentation, SegmentationMedia

def main():
    """
    Submit a job to run ina speech segmenter on HPC
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("root_dir", help="Galaxy root directory")
    parser.add_argument("input", help="input audio file")
    parser.add_argument("segments", help="INA Speech Segmenter output")
    parser.add_argument("amp_segments", help="AMP Segmentation Schema output")
    parser.add_argument("hpc_timestamps", help="HPC Timestamps output")
    args = parser.parse_args()

    # set up logging
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(message)s")

    config = mgm_utils.get_config(args.root_dir)
    dropbox = config["hpc"]["dropbox"]
    
    # job parameters    
    job = {
        'script': 'ina_speech_segmenter',
        'input_map': {
            'input': args.input
        },
        'output_map': {
            'segments': args.segments
        }
    }
    print("Submitting job to HPC")
    job = hpc_submit.submit_and_wait(dropbox, job)

    print("Checking job status: " + job['job']['status'])
    if job['job']['status'] != 'ok':
        exit(1)

    print("Reading TSV into list of tuples")
    with open(args.segments, 'r') as csvin:
        data=[tuple(line) for line in csv.reader(csvin, delimiter='\t')]

    print("Converting ina output  to segmentation schema")
     # Convert the resulting list of tuples to an object for serialization
    seg_schema = convert_to_segmentation_schema(args.input, data)

    print("Writing output json")
    # Serialize the json and write it to destination file
    write_output_json(seg_schema, args.amp_segments)

    print("Job output:")
    print(job)

    # Write the hpc timestamps output
    if "start" in job['job'].keys() and "end" in job['job'].keys():
        ts_output = {
            "start_time": job['job']["start"],
            "end_time": job['job']["end"],
            "elapsed_time": (datetime.strptime(job['job']["end"], '%Y-%m-%dT%H::%M::%S.%f') - datetime.strptime(job['job']["start"], '%Y-%m-%dT%H::%M::%S.%f')).total_seconds()  
        }
        write_output_json(ts_output, args.hpc_timestamps)

    exit(0)


def convert_to_segmentation_schema(filename, segmentation):
    media = SegmentationMedia()
    media.filename = filename
    # Create a segmentation object to serialize
    seg_schema = Segmentation(media = media)

    # For each segment returned by the ina_speech_segmenter, add 
    # a corresponding segment formatted to json spec
    row = 0
    for segment in segmentation:
        row+=1
        if row == 1:
            continue
        seg_schema.addSegment(segment[0], segment[0], float(segment[1]), float(segment[2]))
    return seg_schema

# Serialize schema obj and write it to output file
def write_output_json(data, json_file):
    # Serialize the segmentation object
    with open(json_file, 'w') as outfile:
        json.dump(data, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
    main()