from galaxy.jobs import JobDestination
from galaxy.jobs.mapper import JobMappingException
import logging
import os
import pynvml as nvml
log = logging.getLogger(__name__)
nvml.nvmlInit()
gpu_count = nvml.nvmlDeviceGetCount()
#gpu_count = 1
def dynamic_fun(tool,job):
    flag = 0
    os.path.join('GALAXY_GPU_ENABLED', 'false')
    os.environ['GALAXY_GPU_ENABLED'] = "false"

    if tool:
        reqmnts = tool.requirements
        for req in reqmnts:
            if req.type == "compute" and req.name == "gpu":
                flag = 1
        if gpu_count > 0 and flag == 1:
            os.environ['GALAXY_GPU_ENABLED'] = "true"
            return "local_gpu"
        else:
            os.environ['GALAXY_GPU_ENABLED'] = "false"
            return "local_cpu"
    else:
        return "local_cpu"