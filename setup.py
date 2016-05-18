import os
import sys

from setuptools import setup, find_packages


readme = open('README.rst').read()

GALAXY_PACKAGE = os.environ.get("GALAXY_PACKAGE", "galaxy-lib")
VERSION = None


def _find_packages(base):
    r = []
    for sub in find_packages(os.sep.join(['lib'] + base.split('.'))):
        print 'Found package', '.'.join([base, sub])
        r.append('.'.join([base, sub]))
    return r


if GALAXY_PACKAGE == "galaxy-lib":
    requirements = []
    base_packages = [
        'galaxy.datatypes',
        'galaxy.exceptions',
        'galaxy.jobs.metrics',
        'galaxy.objectstore',
        'galaxy.tools',
        'galaxy.util',
    ]
    package_data = [
        'exceptions/error_codes.json',
        'datatypes/converters/*.xml',
        'datatypes/display_applications/configs/*/*.xml',
        'datatypes/set_metadata_tool.xml',
        'tools/imp_exp/imp_history_from_archive.xml',
        'tools/imp_exp/exp_history_to_archive.xml',
    ]
elif GALAXY_PACKAGE == "galaxy":
    requirements = [
        'galaxy-lib',
    ]
    base_packages = [
        'galaxy.actions',
        'galaxy.auth',
        'galaxy.dataset_collections',
        'galaxy.dependencies',
        'galaxy.external_services',
        'galaxy.forms',
        'galaxy.jobs',
        'galaxy.managers',
        'galaxy.model',
        'galaxy.openid',
        'galaxy.quota',
        'galaxy.sample_tracking',
        'galaxy.security',
        'galaxy.tags',
        'galaxy.tours',
        'galaxy.visualization',
        'galaxy.web',
        'galaxy.webapps',
        'galaxy.workflow',
        'galaxy.work',
    ]
    package_data = [
        'jobs/runners/util/job_script/DEFAULT_JOB_FILE_TEMPLATE.sh',
        'jobs/runners/util/job_script/CLUSTER_SLOTS_STATEMENT.sh',
        'model/migrate/migrate.cfg',
        'dependencies/*.txt',
    ]
elif GALAXY_PACKAGE == 'tool-shed':
    requirements = [
        'galaxy-app',
    ]
    packages = ['tool_shed'] + _find_packages('tool_shed')
    package_data = []
else:
    sys.stderr.write('ERROR: Unknown package name: {}\n'.format(GALAXY_PACKAGE))
    sys.exit(1)


if GALAXY_PACKAGE.startswith('galaxy'):
    packages = ['galaxy']
    for base_package in base_packages:
        packages.append(base_package)
        packages.extend(_find_packages(base_package))


# sets VERSION (also VERSION_MAJOR and VERSION_MINOR)
execfile('lib/galaxy/version.py')

scripts = ["scripts/galaxy"]

setup(
    name=GALAXY_PACKAGE,
    version=VERSION,
    description='Galaxy (http://galaxyproject.org/).',
    long_description=readme,
    author='Galaxy Project',
    author_email='galaxy-dev@lists.galaxyproject.org',
    url='https://github.com/galaxyproject/galaxy',
    packages=packages,
    entry_points='''
        [console_scripts]
        galaxy-paster=galaxy.util.pastescript.serve:run
        galaxy-main=galaxy.main:main
    ''',
    scripts=scripts,
    package_data={
        'galaxy': package_data,
        'tool_shed': [
            'galaxy_install/migrate/migrate.cfg',
            'scripts/bootstrap_tool_shed/parse_run_sh_args.sh',
            'scripts/bootstrap_tool_shed/bootstrap_tool_shed.sh',
            'scripts/bootstrap_tool_shed/user_info.xml',
        ],
    },
    package_dir={'': 'lib'},
    include_package_data=True,
    install_requires=requirements,
    license="Academic Free License 3.0",
    zip_safe=False,
    keywords='galaxy',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Environment :: Console',
        'License :: OSI Approved :: Academic Free License (AFL)',
        'Operating System :: POSIX',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
    test_suite='test'
)
