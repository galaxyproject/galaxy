"""Linter for CWL tools."""

lint_tool_types = ["cwl"]

from galaxy.tool_util.cwl.schema import schema_loader


def lint_cwl_validation(tool_source, lint_ctx):
    """Determine in CWL tool validates against spec."""
    raw_reference = schema_loader.raw_process_reference(tool_source._source_path)
    validation_exception = None
    try:
        schema_loader.process_definition(raw_reference)
    except Exception as e:
        validation_exception = e
    if validation_exception:
        lint_ctx.error(f"Failed to valdiate CWL artifact: {validation_exception}")
    else:
        lint_ctx.info("CWL appears to be valid.")


def lint_new_draft(tool_source, lint_ctx):
    """Determine in CWL tool is valid, modern draft."""
    raw_reference = schema_loader.raw_process_reference(tool_source._source_path)
    cwl_version = raw_reference.process_object.get("cwlVersion", None)
    if cwl_version is None:
        lint_ctx.error("CWL file does not contain a 'cwlVersion'")
    if cwl_version not in ["v1.0"]:
        lint_ctx.warn(f"CWL version [{cwl_version}] is unknown, we recommend the v1.0 the stable release.")
    else:
        lint_ctx.info(f"Modern CWL version [{cwl_version}].")


def lint_docker_image(tool_source, lint_ctx):
    _, containers, *_ = tool_source.parse_requirements_and_containers()
    if len(containers) == 0:
        lint_ctx.warn("Tool does not specify a DockerPull source.")
    else:
        identifier = containers[0].identifier
        lint_ctx.info(f"Tool will run in Docker image [{identifier}].")


def lint_description(tool_source, lint_ctx):
    help = tool_source.parse_help()
    if not help:
        lint_ctx.warn("Description of tool is empty or absent.")
    elif "TODO" in help:
        lint_ctx.warn("Help contains TODO text.")
