#!/usr/bin/env python

import argparse
import logging
from glob import glob

try:
    import requests
except ImportError:
    requests = None

try:
    from html.parser import HTMLParser
except ImportError:  # python 2
    from HTMLParser import HTMLParser

QUAY_API_ENDPOINT = 'https://quay.io/api/v1/repository'


def get_quay_containers(repository='biocontainers'):
    """
    Get all quay containers in the biocontainers repo
        # >>> lst = get_quay_containers()
        # >>> 'samtools:1.0--1' in lst
        # True
        # >>> 'abricate:0.4--pl5.22.0_0' in lst
        # True
        # >>> 'samtools' in lst
        # False
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
            "%s/%s/%s" % (QUAY_API_ENDPOINT, repository, repo['name']))
        tags = tags_response.json()['tags']
        for tag in tags:
            containers.append('%s:%s' % (repo['name'], tag))

    return containers


def get_singularity_containers():
    """
    Get all existing singularity containers from "https://depot.galaxyproject.org/singularity/"
    >>> lst = get_singularity_containers()
    >>> 'aragorn:1.2.36--1' in lst
    True
    >>> 'znc:latest' in lst
    False
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
    index = requests.get("https://depot.galaxyproject.org/singularity/")
    parser.feed(index.text)
    return parser.containers


def get_conda_envs(filepath):
    """
    Get list of already existing envs
    # >>> t = get_conda_envs()
    # >>> 'samtools:latest' in t
    # True
    """
    return [n.split('__')[-1].replace('@', ':') for n in glob('%s/*' % filepath)]


def get_missing_containers(quay_list, singularity_list, blacklist_file=None):
    r"""
    Return list of quay containers that do not exist as singularity containers. Files stored in a blacklist will be ignored
    >>> from os import remove
    >>> with open('/tmp/blacklist.txt', 'w') as f:
    ...     f.write('l\n\ng\nn\nr')
    8
    >>> get_missing_containers(quay_list=['1', '2', '3', 'h', 'g', 'r'], singularity_list=['3', '4', '5'], blacklist_file='/tmp/blacklist.txt')
    ['1', '2', 'h']
    >>> remove('/tmp/blacklist.txt')
    """
    blacklist = []
    if blacklist_file:
        blacklist = open(blacklist_file).read().split('\n')
    return [n for n in quay_list if n not in singularity_list and n not in blacklist]


def get_missing_envs(quay_list, conda_list, blacklist_file=None):
    r"""
    >>> from os import remove
    >>> with open('/tmp/blacklist.txt', 'w') as f:
    ...     f.write('l\n\ng\nn\nr')
    8
    >>> get_missing_envs(quay_list=['1', '2', '3', 'h--1', 'g--2', 'r'], conda_list=['3', '4', '5'], blacklist_file='/tmp/blacklist.txt')
    ['1', '2', 'h--1']
    """
    blacklist = []
    if blacklist_file:
        blacklist = open(blacklist_file).read().split('\n')

    return [n for n in quay_list if n.split('--')[0] not in conda_list and n.split('--')[0] not in blacklist]


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
    parser.add_argument('-b', '--blacklist', dest='blacklist', default=None,
                        help="Provide a 'blacklist file' containing containers which should be excluded from the list.")
    parser.add_argument('-f', '--file', dest='output', default=None,
                        help="File to write list to. If not given output will be returned on the command line.")

    args = parser.parse_args()

    if args.source == 'docker':
        containers = get_quay_containers()
        if args.not_singularity:
            containers = get_missing_containers(
                containers, get_singularity_containers(), args.blacklist)
        if args.not_conda:
            containers = get_missing_envs(containers, get_conda_envs(
                args.conda_filepath), args.blacklist)
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
                f.write('%s\n' % container)
    else:
        print(containers)


if __name__ == '__main__':
    # main()

    import doctest
    doctest.testmod()
