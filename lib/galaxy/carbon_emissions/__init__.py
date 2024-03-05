import csv
import json
import logging
import os
from typing import List

log = logging.getLogger(__name__)


class CarbonIntensityEntry:
    def __init__(self, location_name: str, carbon_intensity: float):
        self.location_name = location_name
        self.carbon_intensity = carbon_intensity


class AWSInstanceCPU:
    def __init__(self, cpu_model: str, tdp: int, core_count: int, source: str):
        self.cpu_model = cpu_model
        self.tdp = tdp
        self.core_count = core_count
        self.source = source


class AWSInstance:
    def __init__(self, name: str, mem: float, v_cpu_count: int, cpu: List[AWSInstanceCPU]):
        self.name = name
        self.mem = mem
        self.v_cpu_count = v_cpu_count
        self.cpu = cpu


def get_carbon_intensity_entry(geographical_server_location_code: str) -> CarbonIntensityEntry:
    """
    Gets the name and carbon intensity value of the geographical location corresponding to
    'geographical_server_location_code'.
    """
    carbon_emissions_dir = os.path.join(os.path.dirname(__file__), "carbon_intensity.csv")

    for location_entry in _load_locations(carbon_emissions_dir):
        location_code, location_name = location_entry[0], location_entry[2]

        is_region = len(location_code) > 2
        if is_region:
            region_name = location_entry[3]
            location_name = f"{region_name} ({location_name})"

        if location_code == geographical_server_location_code:
            return CarbonIntensityEntry(location_name=location_name, carbon_intensity=float(location_entry[4]))

    log.warning("No corresponding location name exists for location code: %s.", geographical_server_location_code)
    log.info("Using global default values for location name and carbon intensity...")
    return CarbonIntensityEntry(location_name="GLOBAL", carbon_intensity=475.0)


def load_aws_ec2_reference_data_json() -> List[AWSInstance]:
    """
    Load the AWS EC2 reference data from the specified file.
    """
    aws_ec2_reference_data_dir = os.path.join(os.path.dirname(__file__), "aws_ec2_reference_data.json")
    with open(aws_ec2_reference_data_dir) as f:
        return json.load(f)


def _load_locations(path: str):
    with open(path, newline="") as f:
        csv_reader = csv.reader(f, delimiter=",")
        yield from csv_reader
