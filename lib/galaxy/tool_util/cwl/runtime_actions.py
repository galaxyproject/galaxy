import json
import os
import shutil
from typing import Optional

from galaxy.util import safe_makedirs
from .cwltool_deps import ref_resolver
from .parser import (
    JOB_JSON_FILE,
    load_job_proxy,
)
from .util import (
    SECONDARY_FILES_INDEX_PATH,
    STORE_SECONDARY_FILES_WITH_BASENAME,
)


def file_dict_to_description(file_dict):
    output_class = file_dict["class"]
    assert output_class in ["File", "Directory"], file_dict
    location = file_dict["location"]
    if location.startswith("_:"):
        assert output_class == "File"
        return LiteralFileDescription(file_dict["contents"])
    elif output_class == "File":
        return PathFileDescription(_possible_uri_to_path(location))
    else:
        return PathDirectoryDescription(_possible_uri_to_path(location))


class FileDescription:
    pass


class PathFileDescription:
    def __init__(self, path):
        self.path = path

    def write_to(self, destination):
        # TODO: Move if we can be sure this is in the working directory for instance...
        shutil.copy(self.path, destination)


class PathDirectoryDescription:
    def __init__(self, path):
        self.path = path

    def write_to(self, destination):
        shutil.copytree(self.path, destination)


class LiteralFileDescription:
    def __init__(self, content):
        self.content = content

    def write_to(self, destination):
        with open(destination, "wb") as f:
            f.write(self.content.encode("UTF-8"))


def _possible_uri_to_path(location):
    if location.startswith("file://"):
        path = ref_resolver.uri_file_path(location)
    else:
        path = location
    return path


def handle_outputs(job_directory: Optional[str] = None):
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

    cwl_metadata_params_path = os.path.join(job_directory, "cwl_params.json")
    with open(cwl_metadata_params_path) as f:
        cwl_metadata_params = json.load(f)
    job_id_tag = cwl_metadata_params["job_id_tag"]
    from galaxy.job_execution.output_collect import (
        default_exit_code_file,
        read_exit_code_from,
    )

    exit_code_file = default_exit_code_file(".", job_id_tag)
    tool_exit_code = read_exit_code_from(exit_code_file, job_id_tag)
    outputs = job_proxy.collect_outputs(tool_working_directory, tool_exit_code)

    # Build galaxy.json file.
    provided_metadata = {}

    def move_directory(output, target_path, output_name=None):
        assert output["class"] == "Directory"
        output_path = _possible_uri_to_path(output["location"])
        if output_path.startswith("_:"):
            assert "listing" in output, "Do not know how to handle output, no 'listing' found."
            listing = output["listing"]
            # No a real path, just copy listing to target path.
            safe_makedirs(target_path)
            for listed_file in listing:
                # TODO: handle directories
                assert listed_file["class"] == "File"
                file_description = file_dict_to_description(listed_file)
                file_description.write_to(os.path.join(target_path, listed_file["basename"]))
        else:
            shutil.move(output_path, target_path)
        return {"created_from_basename": output["basename"]}

    def move_output(output, target_path, output_name=None):
        assert output["class"] == "File"
        file_description = file_dict_to_description(output)
        file_description.write_to(target_path)

        secondary_files = output.get("secondaryFiles", [])
        if secondary_files:
            order = []
            index_contents = {"order": order}

            for secondary_file in secondary_files:
                if output_name is None:
                    raise NotImplementedError("secondaryFiles are unimplemented for dynamic list elements")

                # TODO: handle nested files...
                secondary_file_description = file_dict_to_description(secondary_file)
                # assert secondary_file_path.startswith(output_path), "[%s] does not start with [%s]" % (secondary_file_path, output_path)
                secondary_file_basename = secondary_file["basename"]

                if not STORE_SECONDARY_FILES_WITH_BASENAME:
                    output_basename = output["basename"]
                    prefix = ""
                    while True:
                        if secondary_file_basename.startswith(output_basename):
                            secondary_file_name = prefix + secondary_file_basename[len(output_basename) :]
                            break
                        prefix = f"^{prefix}"
                        if "." not in output_basename:
                            secondary_file_name = prefix + secondary_file_name
                            break
                        else:
                            output_basename = output_basename.rsplit(".", 1)[0]
                else:
                    secondary_file_name = secondary_file_basename
                # Convert to ^ format....
                secondary_files_dir = job_proxy.output_secondary_files_dir(output_name, create=True)
                extra_target = os.path.join(secondary_files_dir, secondary_file_name)
                secondary_file_description.write_to(extra_target)
                order.append(secondary_file_name)

            with open(os.path.join(secondary_files_dir, "..", SECONDARY_FILES_INDEX_PATH), "w") as f:
                json.dump(index_contents, f)

        return {"created_from_basename": output["basename"]}

    def handle_known_output(output, output_key, output_name):
        # if output["class"] != "File":
        #    # This case doesn't seem like it would be reached - why is this here?
        #    provided_metadata[output_name] = {
        #        "ext": "expression.json",
        #    }
        # else:
        assert output_name
        if output["class"] == "File":
            target_path = job_proxy.output_path(output_name)
            file_metadata = move_output(output, target_path, output_name=output_name)
        elif output["class"] == "Directory":
            target_path = job_proxy.output_directory_contents_dir(output_name)
            file_metadata = move_directory(output, target_path, output_name=output_name)
        else:
            raise Exception(f"Unknown output type [{output}] encountered")
        provided_metadata[output_name] = file_metadata

    def handle_known_output_json(output, output_name):
        target_path = job_proxy.output_path(output_name)
        with open(target_path, "w") as f:
            f.write(json.dumps(output))
        provided_metadata[output_name] = {
            "ext": "expression.json",
        }

    handled_outputs = []
    for output_name, output in outputs.items():
        handled_outputs.append(output_name)
        if isinstance(output, dict) and "location" in output:
            handle_known_output(output, output_name, output_name)
        elif isinstance(output, dict):
            prefix = f"{output_name}|__part__|"
            for record_key, record_value in output.items():
                record_value_output_key = f"{prefix}{record_key}"
                if isinstance(record_value, dict) and "class" in record_value:
                    handle_known_output(record_value, record_value_output_key, output_name)
                else:
                    # param_evaluation_noexpr
                    handle_known_output_json(output, output_name)

        elif isinstance(output, list):
            elements = []
            for index, el in enumerate(output):
                if isinstance(el, dict) and el["class"] == "File":
                    output_path = _possible_uri_to_path(el["location"])
                    elements.append(
                        {"name": str(index), "filename": output_path, "created_from_basename": el["basename"]}
                    )
                else:
                    target_path = f"{output_name}____{str(index)}"
                    with open(target_path, "w") as f:
                        f.write(json.dumps(el))
                    elements.append({"name": str(index), "filename": target_path, "ext": "expression.json"})
            provided_metadata[output_name] = {"elements": elements}
        else:
            handle_known_output_json(output, output_name)

    for output_instance in job_proxy._tool_proxy.output_instances():
        output_name = output_instance.name
        if output_name not in handled_outputs:
            handle_known_output_json(None, output_name)

    job_metadata = os.path.join(job_directory, cwl_metadata_params["job_metadata"])
    with open(job_metadata, "w") as f:
        json.dump(provided_metadata, f)


__all__ = ("handle_outputs",)
