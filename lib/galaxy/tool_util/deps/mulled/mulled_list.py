#!/usr/bin/env python

import argparse
import logging
from glob import glob
from html.parser import HTMLParser

import requests

from .util import MULLED_SOCKET_TIMEOUT

QUAY_API_ENDPOINT = 'https://quay.io/api/v1/repository'


def get_quay_containers(repository='biocontainers'):
    """
    Get all quay containers in the biocontainers repo
    """
    containers = []

    repos_parameters = {'public': 'true', 'namespace': repository}
    repos_headers = {'Accept-encoding': 'gzip', 'Accept': 'application/json'}
    repos_response = requests.get(
        QUAY_API_ENDPOINT, headers=repos_headers, params=repos_parameters, timeout=12)

    repos = repos_response.json()['repositories']

    for repo in repos:
        logging.info(repo)
        tags_response = requests.get(
            f"{QUAY_API_ENDPOINT}/{repository}/{repo['name']}",
            timeout=MULLED_SOCKET_TIMEOUT)
        tags = tags_response.json()['tags']
        for tag in tags:
            containers.append(f"{repo['name']}:{tag}")

    return containers


def get_singularity_containers():
    """
    Get all existing singularity containers from "https://depot.galaxyproject.org/singularity/"
    """
    class GetContainerNames(HTMLParser):  # small parser which gets list of containers
        def __init__(self):
            HTMLParser.__init__(self)
            self.containers = []

        def handle_starttag(self, tag, attrs):
            try:
                for attr in attrs:
                    if attr[0] == 'href' and attr[1] != '../':
                        self.containers.append(attr[1].replace('%3A', ':'))
            except IndexError:
                pass

    parser = GetContainerNames()
    index = requests.get("https://depot.galaxyproject.org/singularity/", timeout=MULLED_SOCKET_TIMEOUT)
    parser.feed(index.text)
    return parser.containers


def get_conda_envs(filepath):
    """
    Get list of already existing envs
    """
    return [n.split('__')[-1].replace('@', ':') for n in glob(f'{filepath}/*')]


def get_missing_containers(quay_list, singularity_list, blocklist_file=None):
    r"""
    Return list of quay containers that do not exist as singularity containers. Files stored in a blocklist will be ignored
    """
    blocklist = []
    if blocklist_file:
        with open(blocklist_file) as fh:
            blocklist = fh.read().split('\n')
    return [n for n in quay_list if n not in singularity_list and n not in blocklist]


def get_missing_envs(quay_list, conda_list, blocklist_file=None):
    r"""
    Compares list of conda envs and docker containers and returns missing conda envs
    """
    blocklist = []
    if blocklist_file:
        with open(blocklist_file) as fh:
            blocklist = fh.read().split('\n')

    return [n for n in quay_list if n.split('--')[0] not in conda_list and n.split('--')[0] not in blocklist]


def main():
    parser = argparse.ArgumentParser(
        description='Returns list of Docker containers in the quay.io biocontainers repository.')
    parser.add_argument('--source', '-s',
                        help="Docker, Singularity or Conda.")
    parser.add_argument('--not-singularity', dest='not_singularity', action="store_true",
                        help="Exclude Docker containers from which Singularity containers have already been built.")
    parser.add_argument('--not-conda', dest='not_conda', action="store_true",
                        help="Exclude Docker containers from which Conda environments have already been extracted.")
    parser.add_argument('--conda-filepath', dest='conda_filepath', default=None,
                        help="If searching for conda environments or employing the --not-conda option, a filepath where the environments are located.")
    parser.add_argument('-b', '--blocklist', '--blacklist', dest='blocklist', default=None,
                        help="Provide a 'blocklist file' containing containers which should be excluded from the list.")
    parser.add_argument('-f', '--file', dest='output', default=None,
                        help="File to write list to. If not given output will be returned on the command line.")

    args = parser.parse_args()

    if args.source == 'docker':
        containers = get_quay_containers()
        if args.not_singularity:
            containers = get_missing_containers(
                containers, get_singularity_containers(), args.blocklist)
        if args.not_conda:
            containers = get_missing_envs(containers, get_conda_envs(
                args.conda_filepath), args.blocklist)
    elif args.source == 'singularity':
        containers = get_singularity_containers()
    elif args.source == 'conda':
        containers = get_conda_envs(args.conda_filepath)
    else:
        print("The 'source' argument was not understood.")
        return

    if args.output:
        with open(args.output, 'a') as f:
            for container in containers:
                f.write(f'{container}\n')
    else:
        print(containers)


if __name__ == '__main__':
    main()
