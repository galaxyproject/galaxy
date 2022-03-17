#!/usr/bin/env python

import argparse
import subprocess
import tempfile
from glob import glob
from subprocess import check_output

from galaxy.util import unicodify
from .get_tests import hashed_test_search, main_test_search


def get_list_from_file(filename):
    """
    Returns a list of containers stored in a file (one on each line)
    """
    with open(filename) as fh:
        return [_ for _ in fh.read().splitlines() if _]  # if blank lines are in the file empty strings must be removed


def docker_to_singularity(container, installation, filepath, no_sudo=False):
    """
    Convert docker to singularity container.
    """
    cmd = [installation, 'build', '/'.join((filepath, container)), f"docker://quay.io/biocontainers/{container}"]
    try:
        if no_sudo:
            check_output(cmd, stderr=subprocess.STDOUT)
        else:
            check_output(cmd.insert(0, 'sudo'), stderr=subprocess.STDOUT)
            check_output(['sudo', 'rm', '-rf', '/root/.singularity/docker/'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Docker to Singularity conversion failed.\nOutput was:\n{unicodify(e.output)}")


def singularity_container_test(tests, installation, filepath):
    """
    Run tests, record if they pass or fail
    """
    test_results = {'passed': [], 'failed': [], 'notest': []}

    # create a 'sanitised home' directory in which the containers may be mounted - see http://singularity.lbl.gov/faq#solution-1-specify-the-home-to-mount
    with tempfile.TemporaryDirectory() as tmpdirname:
        for container, test in tests.items():
            if 'commands' not in test and 'imports' not in test:
                test_results['notest'].append(container)

            else:
                exec_command = [installation, 'exec', '-H', tmpdirname, '/'.join((filepath, container))]
                test_passed = True
                errors = []
                if test.get('commands', False):
                    for test_command in test['commands']:
                        test_command = test_command.replace('$PREFIX', '/usr/local/')
                        test_command = test_command.replace('${PREFIX}', '/usr/local/')
                        test_command = test_command.replace('$R ', 'Rscript ')

                        try:
                            check_output(exec_command.extend(['bash', '-c', test_command]), stderr=subprocess.STDOUT)
                        except subprocess.CalledProcessError:
                            try:
                                check_output(exec_command.append(test_command), stderr=subprocess.STDOUT)
                            except subprocess.CalledProcessError as e:
                                errors.append(
                                    {'command': test_command, 'output': unicodify(e.output)})
                                test_passed = False

                if test.get('imports', False):
                    for imp in test['imports']:
                        try:
                            check_output(exec_command.extend([test['import_lang'], f"import {imp}"]), stderr=subprocess.STDOUT)
                        except subprocess.CalledProcessError as e:
                            errors.append({'import': imp, 'output': unicodify(e.output)})
                            test_passed = False

                if test_passed:
                    test_results['passed'].append(container)
                else:
                    test['errors'] = errors
                    test_results['failed'].append(test)
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
        container_testing({'anaconda_channel': 'bioconda', 'installation': args.installation, 'filepath': args.filepath, 'github_repo': 'bioconda/bioconda-recipes',
              'deep_search': False, 'github_local_path': None, 'logfile': args.testing, 'containers': containers})


def container_testing(args=None):
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
                      for n in glob(f"{args['filepath']}*")]

    with open(args['logfile'], 'w') as f:
        f.write("SINGULARITY CONTAINERS GENERATED:")
        tests = {}
        for container in containers:
            if container[0:6] == 'mulled':  # if it is a 'hashed container'
                tests[container] = hashed_test_search(
                    container, args['github_local_path'], args['deep_search'], args['anaconda_channel'], args['github_repo'])
            else:
                tests[container] = main_test_search(
                    container, args['github_local_path'], args['deep_search'], args['anaconda_channel'], args['github_repo'])
        test_results = singularity_container_test(
            tests, args['installation'], args['filepath'])

        f.write('\n\tTEST PASSED:')
        for container in test_results['passed']:
            f.write(f'\n\t\t{container}')
        f.write('\n\tTEST FAILED:')
        for container in test_results['failed']:
            f.write(f"\n\t\t{container['container']}")
            for error in container['errors']:
                f.write('\n\t\t\tCOMMAND: {}\n\t\t\t\tERROR:{}'.format(error.get(
                    'command', f"import{error.get('import', 'nothing found')}"), error['output']))
        f.write('\n\tNO TEST AVAILABLE:')
        for container in test_results['notest']:
            f.write(f'\n\t\t{container}')


if __name__ == "__main__":
    main()
