#!/usr/bin/env python

import argparse
import os
import subprocess
from glob import glob
from subprocess import check_output

from galaxy.tools.deps.mulled.get_tests import hashed_test_search, test_search


def get_list_from_file(filename):
    r"""
    Returns a list of containers stored in a file (one on each line)
    >>> from os import remove
    >>> with open('/tmp/list_file.txt', 'w') as f:
    ...     f.write('bbmap:36.84--0\nbiobambam:2.0.42--0\nconnor:0.5.1--py35_0\ndiamond:0.8.26--0\nedd:1.1.18--py27_0')
    >>> get_list_from_file('/tmp/list_file.txt')
    ['bbmap:36.84--0', 'biobambam:2.0.42--0', 'connor:0.5.1--py35_0', 'diamond:0.8.26--0', 'edd:1.1.18--py27_0']
    >>> remove('/tmp/list_file.txt')
    """
    return [n for n in open(filename).read().split('\n') if n != '']  # if blank lines are in the file empty strings must be removed


def docker_to_singularity(container, installation, filepath, no_sudo=False):
    """
    Convert docker to singularity container.
    """

    try:
        if no_sudo:
            check_output("%s build %s/%s docker://quay.io/biocontainers/%s" % (installation, filepath, container, container), stderr=subprocess.STDOUT, shell=True)
        else:
            check_output("sudo %s build %s/%s docker://quay.io/biocontainers/%s && sudo rm -rf /root/.singularity/docker/" % (installation, filepath, container, container), stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        error_info = {'code': e.returncode, 'cmd': e.cmd, 'out': e.output}
        return error_info
    else:
        return None


def test_singularity_container(tests, installation, filepath):
    """
    Run tests, record if they pass or fail
    >>> import os, shutil
    >>> os.mkdir('/tmp/singtest')
    >>> for n in ['pybigwig:0.1.11--py36_0', 'samtools:1.0--1', 'yasm:1.3.0--0']:
    ...     docker_to_singularity(n, 'singularity', '/tmp/singtest', no_sudo=True)
    >>> results = test_singularity_container({'pybigwig:0.1.11--py36_0': {'imports': ['pyBigWig'], 'commands': ['python -c "import pyBigWig; assert(pyBigWig.numpy == 1); assert(pyBigWig.remote == 1)"'], 'import_lang': 'python -c'}, 'samtools:1.0--1': {'commands': ['samtools --help'], 'import_lang': 'python -c', 'container': 'samtools:1.0--1'}, 'yasm:1.3.0--0': {}}, 'singularity', '/tmp/singtest')
    >>> 'samtools:1.0--1' in results['passed']
    True
    >>> results['failed'][0]['imports'] == ['pyBigWig']
    True
    >>> 'yasm:1.3.0--0' in results['notest']
    True
    >>> shutil.rmtree('/tmp/singtest')
    """
    test_results = {'passed': [], 'failed': [], 'notest': []}

    # create a 'sanitised home' directory in which the containers may be mounted - see http://singularity.lbl.gov/faq#solution-1-specify-the-home-to-mount
    os.mkdir("/tmp/sing_home")

    for container, test in tests.items():
        if 'commands' not in test and 'imports' not in test:
            test_results['notest'].append(container)

        else:
            test_passed = True
            errors = []
            if test.get('commands', False):
                for command in test['commands']:
                    command = command.replace('$PREFIX', '/usr/local/')
                    command = command.replace('${PREFIX}', '/usr/local/')
                    command = command.replace('$R ', 'Rscript ')

                    try:
                        check_output("%s exec -H /tmp/sing_home %s/%s bash -c \"%s\"" % (
                            installation, filepath, container, command), stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError:
                        try:
                            check_output("%s exec -H /tmp/sing_home %s/%s %s" % (
                                installation, filepath, container, command), stderr=subprocess.STDOUT, shell=True)
                        except subprocess.CalledProcessError as e:
                            errors.append(
                                {'command': command, 'output': e.output})
                            test_passed = False

            if test.get('imports', False):
                for imp in test['imports']:
                    try:
                        check_output("%s exec -H /tmp/sing_home %s/%s %s 'import %s'" % (installation, filepath,
                                                                                         container, test['import_lang'], imp), stderr=subprocess.STDOUT, shell=True)
                    except subprocess.CalledProcessError as e:
                        errors.append({'import': imp, 'output': e.output})
                        test_passed = False

            if test_passed:
                test_results['passed'].append(container)
            else:
                test['errors'] = errors
                test_results['failed'].append(test)
    os.rmdir("/tmp/sing_home")
    return test_results


def main():
    parser = argparse.ArgumentParser(
        description='Updates index of singularity containers.')
    parser.add_argument('-c', '--containers', dest='containers', nargs='+', default=None,
                        help="Containers to be generated. If the number of containers is large, it may be simpler to use the --containers-list option.")
    parser.add_argument('-l', '--container-list', dest='container_list', default=None,
                        help="Name of file containing list of containers to be generated. Alternative to --containers.")
    parser.add_argument('-f', '--filepath', dest='filepath',
                        help="File path where newly-built Singularity containers are placed.")
    parser.add_argument('-i', '--installation', dest='installation',
                        help="File path of Singularity installation.")
    parser.add_argument('--no-sudo', dest='no_sudo', action='store_true',
                        help="Build containers without sudo.")
    parser.add_argument('--testing', '-t', dest='testing', default=None,
                        help="Performs testing automatically - a name for the output file should be provided. (Alternatively, testing may be done using the separate testing tool.")

    args = parser.parse_args()

    if args.containers:
        containers = args.containers
    elif args.container_list:
        containers = get_list_from_file(args.container_list)
    else:
        print("Either --containers or --container-list should be selected.")
        return

    for container in containers:
        docker_to_singularity(container, args.installation,
                              args.filepath, args.no_sudo)

    if args.testing:
        test({'anaconda_channel': 'bioconda', 'installation': args.installation, 'filepath': args.filepath, 'github_repo': 'bioconda/bioconda-recipes',
              'deep_search': False, 'github_local_path': None, 'logfile': args.testing, 'containers': containers})


def test(args=None):
    if not args:  # i.e. if testing is called directly from CLI and not via main()
        parser = argparse.ArgumentParser(description='Tests.')
        parser.add_argument('-c', '--containers', dest='containers', nargs='+', default=None,
                            help="Containers to be tested. If the number of containers is large, it may be simpler to use the --containers-list option.")
        parser.add_argument('-l', '--container-list', dest='container_list', default=None,
                            help="Name of file containing list of containers to be tested. Alternative to --containers.")
        parser.add_argument('-f', '--filepath', dest='filepath',
                            help="File path where the containers to be tested are located.")
        parser.add_argument('-o', '--logfile', dest='logfile', default='singularity.log',
                            help="Filename for a log to be written to.")
        parser.add_argument('-i', '--installation', dest='installation',
                            help="File path of Singularity installation.")
        parser.add_argument('--deep-search', dest='deep_search', action='store_true',
                            help="Perform a more extensive, but probably slower, search for tests.")
        parser.add_argument('--anaconda-channel', dest='anaconda_channel', default='bioconda',
                            help="Anaconda channel to search for tests (default: bioconda).")
        parser.add_argument('--github-repo', dest='github_repo', default='bioconda/bioconda-recipes',
                            help="Github repository to search for tests - only relevant if --deep-search is activated (default: bioconda/bioconda-recipes")
        parser.add_argument('--github-local-path', dest='github_local_path', default=None,
                            help="If the bioconda-recipes repository (or other repository containing tests) is available locally, provide the path here. Only relevant if --deep-search is activated.")
        args = vars(parser.parse_args())

    if args['containers']:
        containers = args['containers']
    elif args['container_list']:
        containers = get_list_from_file(args['container_list'])
    else:  # if no containers are specified, test everything in the filepath
        containers = [n.split(args['filepath'])[1]
                      for n in glob('%s*' % args['filepath'])]

    with open(args['logfile'], 'w') as f:
        f.write("SINGULARITY CONTAINERS GENERATED:")
        tests = {}
        for container in containers:
            if container[0:6] == 'mulled':  # if it is a 'hashed container'
                tests[container] = hashed_test_search(
                    container, args['github_local_path'], args['deep_search'], args['anaconda_channel'], args['github_repo'])
            else:
                tests[container] = test_search(
                    container, args['github_local_path'], args['deep_search'], args['anaconda_channel'], args['github_repo'])
        test_results = test_singularity_container(
            tests, args['installation'], args['filepath'])

        f.write('\n\tTEST PASSED:')
        for container in test_results['passed']:
            f.write('\n\t\t%s' % container)
        f.write('\n\tTEST FAILED:')
        for container in test_results['failed']:
            f.write('\n\t\t%s' % container['container'])
            for error in container['errors']:
                f.write('\n\t\t\tCOMMAND: %s\n\t\t\t\tERROR:%s' % (error.get(
                    'command', 'import' + error.get('import', 'nothing found')), error['output']))
        f.write('\n\tNO TEST AVAILABLE:')
        for container in test_results['notest']:
            f.write('\n\t\t%s' % container)


if __name__ == "__main__":
    # main()
    import doctest
    doctest.testmod()
