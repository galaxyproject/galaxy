import sys
import os


ERR_SUFFIX = ".err"

# Cleanup previous error file if exists, and exit with error code 1 if the given (output) file already exists, i.e. generated previously.
# This method should be called by a command with following command depending on it, and might be called repeatedly, such as in HMGM. 
def exit_if_file_generated(file):
    cleanup_err_file(file)
        
    # Since Galaxy creates all output files with size 0 upon starting a job, we can't use the existence of output file 
    # to decide if the output has been created; rather, we can use its file size and/or content as the criteria.
    # If the file has already been generated for ex, by the HMGM converter, exit with error code 1 to avoid redundant process.     
    if not os.path.exists(file) or os.stat(file).st_size == 0:
        exit(1)


# Check if the given (input) file is in error or not ready for processing, exit with error code -1 or 1 respectively.
# This method should be called by a command depending on previous command's completion in a multi-command MGM.
def exit_if_file_not_ready(file):
    # If error file for the given file exists, this indicates previous command (conversion or HMGM task creation) has failed,
    # in which case exit with -1 so the job runner will fail the whole step in ERROR status
    err_file = file + ERR_SUFFIX
    if os.path.exists(err_file):
        exit(-1)
        
    # Since Galaxy creates all output files with size 0 upon starting a job, we can't use the existence of output file 
    # to decide if the output has been created; rather, we can use its file size and/or content as the criteria.
    # If file hasn't been generated for ex, by the HMGM editor, exit with error code 1, 
    # so the HMGM job runner can requeue the step, and p884842rocess will continue to wait for jira to be completed;
    # or if this method is used by non-human MGM, exit 1 will fail the whole step in ERROR status
    if not os.path.exists(file) or os.stat(file).st_size == 0:
        exit(1)
        

# Create an empty error file for the given (output) file.
# This method should be called by an MGM command exiting with error code -1 upon exceptions.
def create_err_file(file):
    # error file has the .err suffix added to the original file path
    err_file = file + ERR_SUFFIX
    with open(err_file, 'w') as fp: 
        pass

# Clean up error file if exists for the given (output) file. 
# This method should be called by an MGM command which could be rerun using the same dependencies after failing with previous error file.
def cleanup_err_file(file):
    err_file = file + ERR_SUFFIX
    if os.path.exists(err_file):
        os.remove(err_file)