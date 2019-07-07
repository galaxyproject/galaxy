#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ast
import os
import re
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

SOURCE_DIR = "galaxy"

_version_re = re.compile(r'__version__\s+=\s+(.*)')

project_short_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
with open('%s/project_galaxy_%s.py' % (SOURCE_DIR, project_short_name), 'rb') as f:
    init_contents = f.read().decode('utf-8')

    def get_var(var_name):
        pattern = re.compile(r'%s\s+=\s+(.*)' % var_name)
        match = pattern.search(init_contents).group(1)
        return str(ast.literal_eval(match))

    version = get_var("__version__")
    PROJECT_NAME = get_var("PROJECT_NAME")
    PROJECT_URL = get_var("PROJECT_URL")
    PROJECT_AUTHOR = get_var("PROJECT_AUTHOR")
    PROJECT_EMAIL = get_var("PROJECT_EMAIL")
    PROJECT_DESCRIPTION = get_var("PROJECT_DESCRIPTION")

TEST_DIR = 'tests'
PACKAGES = [
    'galaxy',
    'galaxy.actions',
    'galaxy.forms',
    'galaxy.jobs',
    'galaxy.jobs.actions',
    'galaxy.jobs.rules',
    'galaxy.jobs.runners',
    'galaxy.jobs.runners.state_handlers',
    'galaxy.jobs.runners.util',
    'galaxy.jobs.runners.util.cli',
    'galaxy.jobs.runners.util.cli.job',
    'galaxy.jobs.runners.util.cli.shell',
    'galaxy.jobs.runners.util.condor',
    'galaxy.jobs.runners.util.job_script',
    'galaxy.jobs.splitters',
    'galaxy.managers',
    'galaxy.openid',
    'galaxy.tools',
    'galaxy.tools.actions',
    'galaxy.tools.data',
    'galaxy.tools.data_manager',
    'galaxy.tools.error_reports',
    'galaxy.tools.expressions',
    'galaxy.tools.filters',
    'galaxy.tools.imp_exp',
    'galaxy.tools.parameters',
    'galaxy.tools.search',
    'galaxy.tools.toolbox',
    'galaxy.tools.toolbox.filters',
    'galaxy.tools.toolbox.lineages',
    'galaxy.tools.util',
    'galaxy.tools.util.galaxyops',
    'galaxy.tools.verify',
    'galaxy.tools.verify.asserts',
    'galaxy.tours',
    'galaxy.visualization',
    'galaxy.visualization.data_providers',
    'galaxy.visualization.data_providers.phyloviz',
    'galaxy.visualization.genome',
    'galaxy.visualization.plugins',
    'galaxy.visualization.tracks',
    'galaxy.webhooks',
    'galaxy.work',
    'galaxy.workflow',
    'galaxy.workflow.resources',
    'galaxy.workflow.schedulers',
    'tool_shed',
    'tool_shed.capsule',
    'tool_shed.dependencies',
    'tool_shed.dependencies.repository',
    'tool_shed.dependencies.tool',
    'tool_shed.galaxy_install.datatypes',
    'tool_shed.galaxy_install.grids',
    'tool_shed.galaxy_install.metadata',
    'tool_shed.galaxy_install.migrate',
    'tool_shed.galaxy_install.migrate.versions',
    'tool_shed.galaxy_install.repository_dependencies',
    'tool_shed.galaxy_install.tool_dependencies',
    'tool_shed.galaxy_install.tool_dependencies.recipe',
    'tool_shed.galaxy_install.tools',
    'tool_shed.galaxy_install.utility_containers',
    'tool_shed.grids',
    'tool_shed.managers',
    'tool_shed.metadata',
    'tool_shed.repository_types',
    'tool_shed.tools',
    'tool_shed.util',
    'tool_shed.utility_containers',
]
ENTRY_POINTS = '''
        [console_scripts]
'''
PACKAGE_DATA = {
    # Be sure to update MANIFEST.in for source dist.
    'galaxy': [
    ],
    'tool_shed': [
        'scripts/bootstrap_tool_shed/user_info.xml',
    ],
}
PACKAGE_DIR = {
    SOURCE_DIR: SOURCE_DIR,
}

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

if os.path.exists("requirements.txt"):
    requirements = open("requirements.txt").read().split("\n")
else:
    # In tox, it will cover them anyway.
    requirements = []


test_requirements = [
    # TODO: put package test requirements here
]


setup(
    name=PROJECT_NAME,
    version=version,
    description=PROJECT_DESCRIPTION,
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    author=PROJECT_AUTHOR,
    author_email=PROJECT_EMAIL,
    url=PROJECT_URL,
    packages=PACKAGES,
    entry_points=ENTRY_POINTS,
    package_data=PACKAGE_DATA,
    package_dir=PACKAGE_DIR,
    include_package_data=True,
    install_requires=requirements,
    license="AFL",
    zip_safe=False,
    keywords='galaxy',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'License :: OSI Approved :: Academic Free License (AFL)',
        'Operating System :: POSIX',
        'Topic :: Software Development',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Testing',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite=TEST_DIR,
    tests_require=test_requirements
)
