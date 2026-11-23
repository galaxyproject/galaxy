"""Names of the job parameters that Galaxy stores alongside a tool's inputs."""

CHROM_INFO = "chromInfo"
DBKEY = "dbkey"
TARGET_DATATYPE = "__target_datatype__"
EXPORT_TO_URI = "__EXPORT_TO_URI__"
ELEMENT_IDENTIFIER_SUFFIX = "|__identifier__"
DATA_MANAGER_MODE = "__data_manager_mode"

# Job parameters that are not tool inputs and that tool templates read: the
# reference genome of the inputs and the target datatype of a datatype converter.
TEMPLATE_JOB_PARAMETERS = frozenset({CHROM_INFO, DBKEY, TARGET_DATATYPE})


def is_element_identifier_parameter(name: str) -> bool:
    """Whether ``name`` holds the collection element identifier of a data input."""
    return name.endswith(ELEMENT_IDENTIFIER_SUFFIX)


def element_identifier_parameter(input_name: str) -> str:
    """Name of the job parameter holding the collection element identifier of data input ``input_name``."""
    return f"{input_name}{ELEMENT_IDENTIFIER_SUFFIX}"
