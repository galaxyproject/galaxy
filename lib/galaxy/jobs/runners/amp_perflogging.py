import json
import time
#
# AMP - gather job performance infomation
#
# 


def common_fields(msgtype, job_wrapper, runner):
    j = job_wrapper
    data = {
        'type': msgtype,
        'time': time.time(),
        'user': j.user,
        'session_id': j.get_session_id(),
        'workflow_invocation_uuid': j.get_param_dict().get('__workflow_invocation_uuid__', None),
        'job_id': j.get_id_tag(),
        'runner': runner,
        'tool_id': j.tool.id,
        'state': j.get_state(),
    }
    return data

def perf_job_queued_msg(job_wrapper, runner):
    data = common_fields("JOB_QUEUED", job_wrapper, runner)
    return json.dumps(data)

def perf_job_started_msg(job_wrapper, runner):
    data = common_fields("JOB_STARTED", job_wrapper, runner)
    job_wrapper._amp_start = time.time()
    return json.dumps(data)    

def perf_job_finished_msg(job_wrapper, runner):
    data = common_fields("JOB_FINISHED", job_wrapper, runner)    
    data['duration'] = time.time() - job_wrapper._amp_start
    data['sizes'] = job_wrapper.get_output_sizes()        
    data['input_filenames'] = job_wrapper.get_input_fnames()
    data['commandline'] = job_wrapper.get_command_line() 
    return json.dumps(data)

def perf_async_submit_msg(job_wrapper, runner):
    data = common_fields("ASYNC_SUBMIT", job_wrapper, runner)
    return json.dumps(data)

def perf_async_submitted_msg(job_wrapper, runner):
    data = common_fields("ASYNC_SUBMITTED", job_wrapper, runner)
    job_wrapper._amp_start = time.time()  # this is to make sure we have a start time.
    return json.dumps(data)
    
