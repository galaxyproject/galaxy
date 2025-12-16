import functools
import json
import logging
import os
import urllib.parse

from cwltool.context import LoadingContext
from cwltool.load_tool import default_loader
from cwltool.pack import pack
from cwltool.utils import visit_field

log = logging.getLogger(__name__)

# https://github.com/common-workflow-language/cwltool/issues/1937
PACKED_WORKFLOWS_CWL_BUG = {
    "conflict-wf.cwl": """
$graph:
- baseCommand: echo
  class: CommandLineTool
  id: echo
  inputs:
    text:
      inputBinding: {}
      type: string
  outputs:
    fileout:
      outputBinding: {glob: out.txt}
      type: File
  stdout: out.txt
- baseCommand: cat
  class: CommandLineTool
  id: cat
  inputs:
    file1:
      inputBinding: {position: 1}
      type: File
    file2:
      inputBinding: {position: 2}
      type: File
  outputs:
    fileout:
      outputBinding: {glob: out.txt}
      type: File
  stdout: out.txt
- class: Workflow
  id: collision
  inputs: {input_1: string, input_2: string}
  outputs:
    fileout: {outputSource: cat_step/fileout, type: File}
  steps:
    cat_step:
      in:
        file1: {source: echo_1/fileout}
        file2: {source: echo_2/fileout}
      out: [fileout]
      run: '#cat'
    echo_1:
      in: {text: input_1}
      out: [fileout]
      run: '#echo'
    echo_2:
      in: {text: input_2}
      out: [fileout]
      run: '#echo'
cwlVersion: v1.1
""",
    "js-expr-req-wf.cwl": """
$graph:
- arguments: [echo, $(foo())]
  class: CommandLineTool
  hints:
    ResourceRequirement: {ramMin: 8}
  id: tool
  inputs: []
  outputs: {out: stdout}
  requirements:
    InlineJavascriptRequirement:
      expressionLib: ['function foo() { return 2; }']
  stdout: whatever.txt
- class: Workflow
  id: wf
  inputs: []
  outputs:
    out: {outputSource: tool/out, type: File}
  requirements:
    InlineJavascriptRequirement:
      expressionLib: ['function bar() { return 1; }']
  steps:
    tool:
      in: {}
      out: [out]
      run: '#tool'
cwlVersion: v1.0
""",
}


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


def get_url(item, cwl_version, base_dir):
    # quick hack, to make it more useful upload files/directories/paths to Galaxy instance ?
    if isinstance(item, dict) and item.get("class") == "File":
        location = item.pop("path", None)
        if not location:
            parse_result = urllib.parse.urlparse(item["location"])
            if parse_result.scheme == "file":
                location = urllib.parse.unquote(parse_result.path)
            if base_dir not in location:
                return item
            location = os.path.relpath(location, base_dir)
        url = f"{get_cwl_test_url(cwl_version)}/{location}"
        log.debug("Rewrote location from '%s' to '%s'", location, url)
        item["location"] = url
    return item


def rewrite_locations(workflow_path: str, output_path: str):
    workflow_path_basename = os.path.basename(workflow_path)
    if workflow_path_basename in PACKED_WORKFLOWS_CWL_BUG:
        with open(output_path, "w") as output:
            output.write(PACKED_WORKFLOWS_CWL_BUG[workflow_path_basename])
            return
    loading_context = LoadingContext()
    loading_context.loader = default_loader()
    workflow_obj = pack(loading_context, workflow_path)
    cwl_version = workflow_path.split("test/functional/tools/cwl_tools/v")[1].split("/")[0]
    # deps = find_deps(workflow_obj, loading_context.loader, uri)
    # basedir=os.path.dirname(workflow_path)
    visit_field(
        workflow_obj,
        ("default"),
        functools.partial(get_url, cwl_version=cwl_version, base_dir=os.path.normpath(os.path.dirname(workflow_path))),
    )
    with open(output_path, "w") as output:
        json.dump(workflow_obj, output)
