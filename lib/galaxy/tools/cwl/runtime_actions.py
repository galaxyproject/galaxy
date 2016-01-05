import os
import shutil

from .parser import (
    JOB_JSON_FILE,
    load_job_proxy,
)


def handle_outputs(job_directory=None):
    # Relocate dynamically collected files to pre-determined locations
    # registered with ToolOutput objects via from_work_dir handling.
    if job_directory is None:
        job_directory = os.getcwd()
    cwl_job_file = os.path.join(job_directory, JOB_JSON_FILE)
    if not os.path.exists(cwl_job_file):
        # Not a CWL job, just continue
        return
    job_proxy = load_job_proxy(job_directory)
    cwl_job = job_proxy.cwl_job()
    outputs = cwl_job.collect_outputs(job_directory)
    for output_name, output in outputs.iteritems():
        target_path = os.path.join(job_directory, "__cwl_output_%s" % output_name)
        shutil.move(output["path"], target_path)


__all__ = [
    'handle_outputs',
]
