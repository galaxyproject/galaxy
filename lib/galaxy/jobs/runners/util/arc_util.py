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
        
        actid_name = SubElement(actid, "Name")
        actid_name.text = "galaxy_arc_hello_test"

        app_out = SubElement(app, "Output")
        app_out.text = self.stdout

        app_err = SubElement(app, "Error")
        app_err.text = self.stderr

        app_exe = SubElement(app, "Executable")
        app_exe_path = SubElement(app_exe, "Path")
        app_exe_path.text = self.exe_path

        for arc_input_name, arc_input_src in self.inputs.items():
            """Datastaging tag"""
            inputfile = SubElement(datastaging, "InputFile")
            
            sub_el = SubElement(inputfile, "Name")
            sub_el.text = arc_input_name
            if 'file://' not in arc_input_src:
                """ Remote source """
                source = SubElement(inputfile, "Source")
                uri = SubElement(source,"URI")
                uri.text = arc_input_src
                

        for arc_output in self.outputs:
            sub_el = SubElement(datastaging, "OutputFile")
            subsub_el = SubElement(sub_el, "Name")
            subsub_el.text = arc_output

        sub_el = SubElement(resources, "IndividualCPUTime")
        sub_el.text = self.cpu_time

        sub_el = SubElement(resources, "IndividualPhysicalMemory")
        sub_el.text = self.memory

        return tostring(descr, encoding="unicode", method="xml")


__all__ = (
    "ensure_pyarc",
    "get_client",
    "ARCJob",
)
