import logging
import multi

log = logging.getLogger( __name__ )

def set_basic_defaults(job_wrapper):
    parent_job = job_wrapper.get_job()
    parallelism = job_wrapper.get_parallelism()
    parallelism.attributes['split_inputs'] = parent_job.input_datasets[0].name
    parallelism.attributes['merge_outputs'] = job_wrapper.get_output_hdas_and_fnames().keys()[0]

def do_split (job_wrapper):
    if len(job_wrapper.get_input_fnames()) > 1 or len(job_wrapper.get_output_fnames()) > 1:
        log.error("The basic splitter is not capable of handling jobs with multiple inputs or outputs.")
        raise Exception,  "Job Splitting Failed, the basic splitter only handles tools with one input and one output"
    # add in the missing information for splitting the one input and merging the one output
    set_basic_defaults(job_wrapper)
    return multi.do_split(job_wrapper)

def do_merge( job_wrapper,  task_wrappers):
    # add in the missing information for splitting the one input and merging the one output
    set_basic_defaults(job_wrapper)
    return multi.do_merge(job_wrapper,  task_wrappers)

