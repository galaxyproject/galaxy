#!/bin/env python3
import argparse
from pathlib import Path
import logging
import sys
import os
sys.path.insert(0, os.path.abspath('../../../../../tools/amp_util'))
import hpc_submit

def main():
    """
    Submit a job to run ina speech segmenter on HPC
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("dropbox", help="hpc_batch dropbox location")
    parser.add_argument("input", help="input audio file")
    parser.add_argument("segments", help="INA Speech Segmenter output")
    args = parser.parse_args()

    # set up logging
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(message)s")

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

    job = hpc_submit.submit_and_wait(args.dropbox, job)
    exit(0 if job['job']['status'] == 'ok' else 1)

if __name__ == "__main__":
    main()