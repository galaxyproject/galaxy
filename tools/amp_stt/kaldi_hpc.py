#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
from pathlib import Path
import logging
import sys

import hpc_submit
import mgm_utils
import kaldi_transcript_to_amp_transcript

def main():
    """
    Submit a job to run ina speech segmenter on HPC
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("root_dir", help="Galaxy root directory")
    parser.add_argument("input", help="input audio file")
    parser.add_argument("kaldi_transcript_json", help="Kaldi JSON output")
    parser.add_argument("kaldi_transcript_txt", help="Kalid TXT output")
    parser.add_argument("amp_transcript_json", help="AMP JSON output")
    parser.add_argument("hpc_timestamps", help="HPC Timestamps output")
    args = parser.parse_args()

    # get hpc dropbox dir path
    dropbox = mgm_utils.get_work_dir(args.root_dir, "hpc_dropbox")
                                    
    # set up logging
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(message)s")
    print("Preparing kaldi HPC job")
    # job parameters    
    job = {
        'script': 'kaldi',
        'input_map': {
            'input': args.input
        },
        'output_map': {
            'kaldi_json': args.kaldi_transcript_json,
            'kaldi_txt': args.kaldi_transcript_txt,
            'amp_json': args.amp_transcript_json
        }
    }
    print("Submitting HPC job")
    job = hpc_submit.submit_and_wait(dropbox, job)

    print("HPC job completed with status: " + job['job']['status'])
    if job['job']['status'] != 'ok':
        exit(1)
        
    print("Convering output to AMP Transcript JSON")
    kaldi_transcript_to_amp_transcript.convert(args.input, args.kaldi_transcript_json, args.kaldi_transcript_txt, args.amp_transcript_json)
    
    print("Job output:")
    print(job)

    # Write the hpc timestamps output
    if "start" in job['job'].keys() and "end" in job['job'].keys():
        ts_output = {
            "start_time": job['job']["start"],
            "end_time": job['job']["end"],
            "elapsed_time": (datetime.strptime(job['job']["end"], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(job['job']["start"], '%Y-%m-%d %H:%M:%S.%f')).total_seconds() 
        }
        with open(args.hpc_timestamps, 'w') as outfile:
            json.dump(ts_output, outfile, default=lambda x: x.__dict__)

    exit(0)

if __name__ == "__main__":
    main()