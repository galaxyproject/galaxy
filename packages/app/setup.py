#!/usr/bin/env python

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
with open(f'{SOURCE_DIR}/project_galaxy_{project_short_name}.py', 'rb') as f:
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
    'galaxy.app_unittest_utils',
    'galaxy.authnz',
    'galaxy.config',
    'galaxy.dependencies',
    'galaxy.forms',
    'galaxy.jobs',
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
    'galaxy.schema',
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
    'galaxy.tools.util',
    'galaxy.tools.util.galaxyops',
    'galaxy.tool_shed',
    'galaxy.tool_shed.galaxy_install',
    'galaxy.tool_shed.galaxy_install.datatypes',
    'galaxy.tool_shed.galaxy_install.metadata',
    'galaxy.tool_shed.galaxy_install.migrate',
    'galaxy.tool_shed.galaxy_install.migrate.versions',
    'galaxy.tool_shed.galaxy_install.repository_dependencies',
    'galaxy.tool_shed.galaxy_install.tool_dependencies',
    'galaxy.tool_shed.galaxy_install.tool_dependencies.recipe',
    'galaxy.tool_shed.galaxy_install.tools',
    'galaxy.tool_shed.util',
    'galaxy.tool_shed.metadata',
    'galaxy.tool_shed.tools',
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
    'galaxy.workflow.refactor',
    'galaxy.workflow.reports',
    'galaxy.workflow.resources',
    'galaxy.workflow.schedulers',
    'galaxy_ext',
    'galaxy_ext.container_monitor',
    'galaxy_ext.expressions',
    'galaxy_ext.metadata',
]
ENTRY_POINTS = '''
        [console_scripts]
        galaxy-main=galaxy.main:main
        galaxy-config=galaxy.config.script:main
'''
PACKAGE_DATA = {
    # Be sure to update MANIFEST.in for source dist.
    'galaxy': [
        'config_schema.yml',
        'job_config_schema.yml',
        'uwsgi_schema.yml',
        'config/sample/*',
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


test_requirements = open("test-requirements.txt").read().split("\n")


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
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    test_suite=TEST_DIR,
    tests_require=test_requirements
)
