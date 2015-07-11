import os
import logging
import shutil
import inspect

from galaxy import model, util


log = logging.getLogger( __name__ )

def do_split (job_wrapper):
    parent_job = job_wrapper.get_job()
    working_directory = os.path.abspath(job_wrapper.working_directory)

    parallel_settings = job_wrapper.get_parallelism().attributes
    # Syntax: split_inputs="input1,input2" shared_inputs="genome"
    # Designates inputs to be split or shared
    split_inputs=parallel_settings.get("split_inputs")
    if split_inputs is None:
        split_inputs = []
    else:
        split_inputs = [x.strip() for x in split_inputs.split(",")]

    shared_inputs=parallel_settings.get("shared_inputs")
    auto_shared_inputs = False
    if shared_inputs is None:
        shared_inputs = []
        auto_shared_inputs = True
    else:
        shared_inputs = [x.strip() for x in shared_inputs.split(",")]
    illegal_inputs = [x for x in shared_inputs if x in split_inputs]
    if len(illegal_inputs) > 0:
        raise Exception("Inputs have conflicting parallelism attributes: %s" % str( illegal_inputs ))

    subdir_index = [0] # use a list to get around Python 2.x lame closure support
    task_dirs = []
    def get_new_working_directory_name():
        dir=os.path.join(working_directory,  'task_%d' % subdir_index[0])
        subdir_index[0] = subdir_index[0] + 1
        if not os.path.exists(dir):
            os.makedirs(dir)
        task_dirs.append(dir)
        return dir

    # For things like paired end alignment, we need two inputs to be split. Since all inputs to all
    # derived subtasks need to be correlated, allow only one input type to be split
    # If shared_inputs are not specified, we assume all non-split inputs are shared inputs.
    # For any input we must consider if each input is None. With optional arguments, a data input could be set to optional
    type_to_input_map = {}
    for input in parent_job.input_datasets:
        if input.dataset is None:
            if input.name in shared_inputs:
                shared_inputs.remove(input.name)
            else:
                pass
        else:
            if input.name in split_inputs:
                type_to_input_map.setdefault(input.dataset.datatype,  []).append(input.name)
            elif input.name in shared_inputs:
                pass # pass original file name
            elif auto_shared_inputs:
                shared_inputs.append(input.name)
            else:
                log_error = "The input '%s' does not define a method for implementing parallelism" % str(input.name)
                log.exception(log_error)
                raise Exception(log_error)

    if len(type_to_input_map) > 1:
        log_error = "The multi splitter does not support splitting inputs of more than one type"
        log.error(log_error)
        raise Exception(log_error)

    # split the first one to build up the task directories
    input_datasets = []
    for input in parent_job.input_datasets:
        if input.name in split_inputs:
            this_input_files = job_wrapper.get_input_dataset_fnames(input.dataset)
            if len(this_input_files) > 1:
                log_error = "The input '%s' is composed of multiple files - splitting is not allowed" % str(input.name)
                log.error(log_error)
                raise Exception(log_error)
            input_datasets.append(input.dataset)

    input_type = type_to_input_map.keys()[0]
    # DBTODO execute an external task to do the splitting, this should happen at refactor.
    # If the number of tasks is sufficiently high, we can use it to calculate job completion % and give a running status.
    try:
        input_type.split(input_datasets, get_new_working_directory_name, parallel_settings)
    except AttributeError:
        log_error = "The type '%s' does not define a method for splitting files" % str(input_type)
        log.error(log_error)
        raise
    log.debug('do_split created %d parts' % len(task_dirs))
    # next, after we know how many divisions there are, add the shared inputs via soft links
    for input in parent_job.input_datasets:
        if input and input.name in shared_inputs:
            names = job_wrapper.get_input_dataset_fnames(input.dataset)
            for dir in task_dirs:
                for file in names:
                    os.symlink(file, os.path.join(dir,  os.path.basename(file)))
    tasks = []
    prepare_files = os.path.join(util.galaxy_directory(), 'extract_dataset_parts.sh') + ' %s'
    for dir in task_dirs:
        task = model.Task(parent_job, dir, prepare_files % dir)
        tasks.append(task)
    return tasks


def do_merge( job_wrapper,  task_wrappers):
    parallel_settings = job_wrapper.get_parallelism().attributes
    # Syntax: merge_outputs="export" pickone_outputs="genomesize"
    # Designates outputs to be merged, or selected from as a representative
    merge_outputs = parallel_settings.get("merge_outputs")
    if merge_outputs is None:
        merge_outputs = []
    else:
        merge_outputs = [x.strip() for x in merge_outputs.split(",")]
    pickone_outputs = parallel_settings.get("pickone_outputs")
    if pickone_outputs is None:
        pickone_outputs = []
    else:
        pickone_outputs = [x.strip() for x in pickone_outputs.split(",")]

    illegal_outputs = [x for x in merge_outputs if x in pickone_outputs]
    if len(illegal_outputs) > 0:
        return ('Tool file error', 'Outputs have conflicting parallelism attributes: %s' % str( illegal_outputs ))

    stdout = ''
    stderr = ''

    try:
        working_directory = job_wrapper.working_directory
        task_dirs = [os.path.join(working_directory, x) for x in os.listdir(working_directory) if x.startswith('task_')]
        assert task_dirs, "Should be at least one sub-task!"
        # TODO: Output datasets can be very complex. This doesn't handle metadata files
        outputs = job_wrapper.get_output_hdas_and_fnames()
        output_paths = job_wrapper.get_output_fnames()
        pickone_done = []
        task_dirs = [os.path.join(working_directory, x) for x in os.listdir(working_directory) if x.startswith('task_')]
        task_dirs.sort(key = lambda x: int(x.split('task_')[-1]))
        for index, output in enumerate( outputs ):
            output_file_name = str( output_paths[ index ] )  # Use false_path if set, else real path.
            base_output_name = os.path.basename(output_file_name)
            if output in merge_outputs:
                output_dataset = outputs[output][0]
                output_type = output_dataset.datatype
                output_files = [os.path.join(dir,base_output_name) for dir in task_dirs]
                # Just include those files f in the output list for which the
                # file f exists; some files may not exist if a task fails.
                output_files = [ f for f in output_files if os.path.exists(f) ]
                if output_files:
                    log.debug('files %s ' % output_files)
                    if len(output_files) < len(task_dirs):
                        log.debug('merging only %i out of expected %i files for %s'
                                  % (len(output_files), len(task_dirs), output_file_name))
                    # First two args to merge always output_files and path of dataset. More
                    # complicated merge methods may require more parameters. Set those up here.
                    extra_merge_arg_names = inspect.getargspec( output_type.merge ).args[2:]
                    extra_merge_args = {}
                    if "output_dataset" in extra_merge_arg_names:
                        extra_merge_args["output_dataset"] = output_dataset
                    output_type.merge(output_files, output_file_name, **extra_merge_args)
                    log.debug('merge finished: %s' % output_file_name)
                else:
                    msg = 'nothing to merge for %s (expected %i files)' \
                          % (output_file_name, len(task_dirs))
                    log.debug(msg)
                    stderr += msg + "\n"
            elif output in pickone_outputs:
                # just pick one of them
                if output not in pickone_done:
                    task_file_name = os.path.join(task_dirs[0], base_output_name)
                    shutil.move( task_file_name,  output_file_name )
                    pickone_done.append(output)
            else:
                log_error = "The output '%s' does not define a method for implementing parallelism" % output
                log.exception(log_error)
                raise Exception(log_error)
    except Exception, e:
        stdout = 'Error merging files';
        log.exception( stdout )
        stderr = str(e)

    for tw in task_wrappers:
        # Prevent repetitive output, e.g. "Sequence File Aligned"x20
        # Eventually do a reduce for jobs that output "N reads mapped", combining all N for tasks.
        out = tw.get_task().stdout.strip()
        err = tw.get_task().stderr.strip()
        if len(out) > 0:
            stdout += "\n" + tw.working_directory + ':\n' + out
        if len(err) > 0:
            stderr += "\n" + tw.working_directory + ':\n' + err
    return (stdout,  stderr)

