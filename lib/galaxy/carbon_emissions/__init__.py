import csv
import json
import logging
import os

from typing_extensions import TypedDict

log = logging.getLogger(__name__)


class CarbonIntensityEntry(TypedDict):
    location_name: str
    carbon_intensity: float


class AWSInstanceCPU(TypedDict):
    cpu_model: str
    tdp: int
    core_count: int
    source: str


class AWSInstance(TypedDict):
    name: str
    mem: float
    v_cpu_count: int
    cpu: list[AWSInstanceCPU]


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
            return {"location_name": location_name, "carbon_intensity": float(location_entry[4])}

    log.warning("No corresponding location name exists for location code: %s.", geographical_server_location_code)
    log.info("Using global default values for location name and carbon intensity...")
    return {"location_name": "GLOBAL", "carbon_intensity": 475.0}


def load_aws_ec2_reference_data_json() -> list[AWSInstance]:
    """
    Load the AWS EC2 reference data from the specified file.
    """
    aws_ec2_reference_data_dir = os.path.join(os.path.dirname(__file__), "aws_ec2_reference_data.json")
    with open(aws_ec2_reference_data_dir, "r") as f:
        return json.load(f)


def _load_locations(path: str):
    with open(path, newline="") as f:
        csv_reader = csv.reader(f, delimiter=",")
        yield from csv_reader
