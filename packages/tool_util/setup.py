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

with open('%s/project_galaxy_tool_util.py' % SOURCE_DIR, 'rb') as f:
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
    'galaxy.tool_util',
    'galaxy.tool_util.client',
    'galaxy.tool_util.cwl',
    'galaxy.tool_util.deps',
    'galaxy.tool_util.deps.container_resolvers',
    'galaxy.tool_util.deps.mulled',
    'galaxy.tool_util.deps.resolvers',
    'galaxy.tool_util.linters',
    'galaxy.tool_util.locations',
    'galaxy.tool_util.parser',
    'galaxy.tool_util.verify',
    'galaxy.tool_util.verify.asserts',
]
ENTRY_POINTS = '''
        [console_scripts]
        galaxy-tool-test=galaxy.tool_util.verify.script:main
        mulled-build=galaxy.tool_util.deps.mulled.mulled_build:main
        mulled-build-channel=galaxy.tool_util.deps.mulled.mulled_build_channel:main
        mulled-search=galaxy.tool_util.deps.mulled.mulled_search:main
        mulled-build-tool=galaxy.tool_util.deps.mulled.mulled_build_tool:main
        mulled-build-files=galaxy.tool_util.deps.mulled.mulled_build_files:main
        mulled-list=galaxy.tool_util.deps.mulled.mulled_list:main
        mulled-update-singularity-containers=galaxy.tool_util.deps.mulled.mulled_update_singularity_containers:main
'''
PACKAGE_DATA = {
    # Be sure to update MANIFEST.in for source dist.
    'galaxy': [
        'tool_util/deps/mulled/invfile.lua',
        'tool_util/deps/resolvers/default_conda_mapping.yml',
        'tool_util/xsd/galaxy.xsd',
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
    extras_require={
        'mulled': [
            'conda',
            'cytoolz',  # cytoolz is an undeclared dependency of the conda package on PyPI
            'jinja2',
            'Whoosh',
        ],
    },
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    test_suite=TEST_DIR,
    tests_require=test_requirements
)
