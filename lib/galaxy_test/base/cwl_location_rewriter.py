import functools
import json
import logging

from cwltool.main import fetch_document
from cwltool.utils import visit_field

log = logging.getLogger(__name__)


def get_cwl_test_url(cwl_version):
    branch = "main"
    if cwl_version == "1.0":
        repo_name = "common-workflow-language"
        tests_dir = "v1.0/v1.0"
    else:
        repo_name = f"cwl-v{cwl_version}"
        tests_dir = "tests"
    if cwl_version == "1.2.1":
        branch = "1.2.1_proposed"
    return f"https://raw.githubusercontent.com/common-workflow-language/{repo_name}/{branch}/{tests_dir}"


def get_url(item, cwl_version):
    # quick hack, to make it more useful upload files/directories/paths to Galaxy instance ?
    if isinstance(item, dict) and item.get("class") == "File":
        location = item.pop("path", None)
        if not location:
            location = item["location"]
        url = f"{get_cwl_test_url(cwl_version)}/{location}"
        log.debug("Rewrote location from '%s' to '%s'", location, url)
        item["location"] = url
    return item


def rewrite_locations(workflow_path: str, output_path: str):
    _loading_context, workflow_obj, _uri = fetch_document(workflow_path)
    cwl_version = workflow_path.split("test/functional/tools/cwl_tools/v")[1].split("/")[0]
    # deps = find_deps(workflow_obj, loading_context.loader, uri)
    # basedir=os.path.dirname(workflow_path)
    visit_field(workflow_obj, ("default"), functools.partial(get_url, cwl_version=cwl_version))
    with open(output_path, "w") as output:
        json.dump(workflow_obj, output)
    return workflow_obj
