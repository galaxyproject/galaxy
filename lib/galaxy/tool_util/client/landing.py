#!/usr/bin/env python

# . .venv/bin/activate; PYTHONPATH=lib python lib/galaxy/tool_util/client/landing.py -g http://localhost:8081 simple_workflow

import argparse
import random
import string
import sys
from dataclasses import dataclass
from typing import Optional

import requests
import yaml

from galaxy.util.resources import resource_string

DESCRIPTION = """
A small utility for demoing creation of tool and workflow landing endpoints.

This allows an external developer to create tool and workflow forms with
pre-populated parameters and handing them off with URLs to their clients/users.
"""
RANDOM_SECRET_LENGTH = 10


def load_default_catalog():
    catalog_yaml = resource_string("galaxy.tool_util.client", "landing_catalog.sample.yml")
    return yaml.safe_load(catalog_yaml)


@dataclass
class Request:
    template_id: str
    catalog: str
    client_secret: Optional[str]
    galaxy_url: str


@dataclass
class Response:
    landing_url: str


def generate_claim_url(request: Request) -> Response:
    template_id = request.template_id
    catalog_path = request.catalog
    galaxy_url = request.galaxy_url
    client_secret = request.client_secret
    if client_secret == "__GEN__":
        client_secret = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(RANDOM_SECRET_LENGTH)
        )
    if catalog_path:
        with open(catalog_path) as f:
            catalog = yaml.safe_load(f)
    else:
        catalog = load_default_catalog()
    template = catalog[template_id]
    template_type = "tool" if "tool_id" in template else "workflow"
    if client_secret:
        template["client_secret"] = client_secret

    landing_request_url = f"{galaxy_url}/api/{template_type}_landings"
    raw_response = requests.post(
        landing_request_url,
        json=template,
    )
    raw_response.raise_for_status()
    response = raw_response.json()
    url = f"{galaxy_url}/{template_type}_landings/{response['uuid']}"
    if client_secret:
        url = url + f"?secret={client_secret}"
    return Response(url)


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("template_id")
    parser.add_argument(
        "-g",
        "--galaxy-url",
        dest="galaxy_url",
        default="https://usegalaxy.org/",
        help="Galxy target for the landing request",
    )
    parser.add_argument(
        "-c",
        "--catalog",
        dest="catalog",
        default=None,
        help="YAML catalog to load landing request templates from.",
    )
    parser.add_argument(
        "-s",
        "--secret",
        dest="secret",
        default=None,
        help="An optional client secret to verify the request against, set to __GEN__ to generate one at random for this request.",
    )
    return parser


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = arg_parser().parse_args(argv)
    request = Request(
        args.template_id,
        args.catalog,
        args.secret,
        args.galaxy_url,
    )
    response = generate_claim_url(request)
    print(f"Your customized form is located at {response.landing_url}")


if __name__ == "__main__":
    main()
