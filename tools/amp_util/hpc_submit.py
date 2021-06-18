"""
Utilities to submit jobs to HPC
"""
from pathlib import Path
import tempfile
from time import sleep
import logging
import yaml

def submit_and_wait(dropbox, job, period=10):
    """
    Submit the job and wait for it to complete
    Return the updated job data (with result information)
    """

    # check the dropbox
    dropbox = Path(dropbox)
    if not dropbox.exists() or not dropbox.is_dir():
        raise NotADirectoryError("Dropbox doesn't exist or isn't a directory")

    # submit the job    
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".job",
                                     dir=dropbox, delete=False) as f:
        result_file = Path(f.name + ".finished")
        logging.debug(f"Job file: {f.name}, result file: {result_file}")
        yaml.dump(job, f)

    # wait for the job to complete
    while not result_file.exists():
        sleep(period)

    # read the results and respond accordingly    
    with open(result_file) as f:
        job = yaml.load(f, Loader=yaml.SafeLoader)
    result_file.unlink()

    logging.debug(f"Job status: {job['job']['status']}, message: {job['job']['message']}")
    logging.debug(f"STDERR: {job['job']['stderr']}")
    logging.debug(f"STDOUT: {job['job']['stdout']}")
    logging.debug(f"Return Code: {job['job']['rc']}")
    logging.debug(job['job'])
    
    return job