import logging
from typing import (
    Dict,
    List,
)
from xml.etree.ElementTree import (
    Element,
    SubElement,
    tostring,
)

try:
    from pyarcrest.arc import (
        ARCJob,
        ARCRest,
        ARCRest_1_1,
    )
    from pyarcrest.errors import (
        ARCHTTPError,
        NoValueInARCResult,
    )

except ImportError:
    ARCHTTPError = None
    NoValueInARCResult = None
    ARCRest_1_1 = None
    ARCJob = None

log = logging.getLogger(__name__)


def ensure_pyarc() -> None:
    if ARCHTTPError is None:
        raise Exception(
            "The configured functionality requires the Python package pyarcrest, but it isn't available in the Python environment."
        )


def get_client(cluster_url: str, token: str) -> ARCRest_1_1:
    return ARCRest.getClient(url=cluster_url, version="1.1", token=token, impls={"1.1": ARCRest_1_1})


class ARCJobBuilder:
    name: str
    stdout: str
    stderr: str
    app: str
    cpu_time: str
    exe_path: str
    memory: str
    inputs: Dict[str, str] = {}
    outputs: List[str] = []
    descrstr: str

    def to_xml_str(self) -> str:
        descr = Element("ActivityDescription")
        descr.set("xmlns", "http://www.eu-emi.eu/es/2010/12/adl")
        descr.set("xmlns:emiestypes", "http://www.eu-emi.eu/es/2010/12/types")
        descr.set("xmlns:nordugrid-adl", "http://www.nordugrid.org/es/2011/12/nordugrid-adl")

        actid = SubElement(descr, "ActivityIdentification")
        app = SubElement(descr, "Application")
        resources = SubElement(descr, "Resources")
        datastaging = SubElement(descr, "DataStaging")

        SubElement(actid, "Name").text = "galaxy_arc_hello_test"
        SubElement(app, "Output").text = self.stdout
        SubElement(app, "Error").text = self.stderr

        app_exe = SubElement(app, "Executable")
        SubElement(app_exe, "Path").text = self.exe_path

        """----------- Begin datastaging ---------"""
        for file_name, file_remote_source in self.inputs.items():
            sub_el = SubElement(datastaging, "InputFile")
            SubElement(sub_el, "Name").text = file_name
            if "file://" not in file_remote_source:
                """Only supply url for remote files, not local ones - local ones are handled by the ARC client on the client side (Galaxy)"""
                source_el = SubElement(sub_el, "Source")
                SubElement(source_el, "URI").text = file_remote_source

        for file_name in self.outputs:
            sub_el = SubElement(datastaging, "OutputFile")
            SubElement(sub_el, "Name").text = file_name
        """----------- End datastaging ---------"""

        SubElement(resources, "IndividualCPUTime").text = self.cpu_time
        SubElement(resources, "IndividualPhysicalMemory").text = self.memory

        return tostring(descr, encoding="unicode", method="xml")


__all__ = (
    "ensure_pyarc",
    "get_client",
    "ARCJob",
)
