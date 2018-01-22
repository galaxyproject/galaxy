import json
import os
import shutil

from .cwltool_deps import ref_resolver
from .parser import (
    JOB_JSON_FILE,
    load_job_proxy,
)


def handle_outputs(job_directory=None):
    # Relocate dynamically collected files to pre-determined locations
    # registered with ToolOutput objects via from_work_dir handling.
    if job_directory is None:
        job_directory = os.path.join(os.getcwd(), os.path.pardir)
    cwl_job_file = os.path.join(job_directory, JOB_JSON_FILE)
    if not os.path.exists(cwl_job_file):
        # Not a CWL job, just continue
        return
    # So we only need to do strict validation when the tool was loaded,
    # no reason to do it again during job execution - so this shortcut
    # allows us to not need Galaxy's full configuration on job nodes.
    job_proxy = load_job_proxy(job_directory, strict_cwl_validation=False)
    tool_working_directory = os.path.join(job_directory, "working")
    outputs = job_proxy.collect_outputs(tool_working_directory)
    for output_name, output in outputs.items():
        target_path = job_proxy.output_path(output_name)
        if isinstance(output, dict) and "location" in output:
            output_path = ref_resolver.uri_file_path(output["location"])
            if output["class"] != "File":
                open("galaxy.json", "w").write(json.dump({
                    "dataset_id": job_proxy.output_id(output_name),
                    "type": "dataset",
                    "ext": "expression.json",
                }))
            shutil.move(output_path, target_path)
            for secondary_file in output.get("secondaryFiles", []):
                # TODO: handle nested files...
                secondary_file_path = ref_resolver.uri_file_path(secondary_file["location"])
                assert secondary_file_path.startswith(output_path)
                secondary_file_name = secondary_file_path[len(output_path):]
                secondary_files_dir = job_proxy.output_secondary_files_dir(
                    output_name, create=True
                )
                extra_target = os.path.join(secondary_files_dir, secondary_file_name)
                shutil.move(
                    secondary_file_path,
                    extra_target,
                )
        else:
            with open(target_path, "w") as f:
                f.write(json.dumps(output))


__all__ = (
    'handle_outputs',
)
