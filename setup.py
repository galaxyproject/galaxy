import sys

from setuptools import setup, find_packages


readme = open('README.rst').read()

# Obviously this should not be empty, but for the moment, use:
# pip install -e git+https://github.com/natefoo/pip@linux-wheels#egg=pip && \
# pip install -r requirements.txt --index-url https://wheels.galaxyproject.org/simple/
requirements = [
]


# sets VERSION (also VERSION_MAJOR and VERSION_MINOR)
execfile('lib/galaxy/version.py')

scripts = ["scripts/galaxy"]

setup(
    name='galaxy',
    version=VERSION,
    description='Galaxy (http://galaxyproject.org/).',
    long_description=readme,
    author='Galaxy Project',
    author_email='galaxy-dev@lists.galaxyproject.org',
    url='https://github.com/galaxyproject/galaxy',
    packages=find_packages('lib'),
    entry_points='''
        [console_scripts]
        galaxy-paster=galaxy.util.pastescript.serve:run
        galaxy-main=galaxy.main:main
    ''',
    scripts=scripts,
    package_data={'galaxy': [
        'exceptions/error_codes.json',
        'jobs/runners/util/job_script/DEFAULT_JOB_FILE_TEMPLATE.sh',
        'jobs/runners/util/job_script/CLUSTER_SLOTS_STATEMENT.sh',
        'model/migrate/migrate.cfg',
        'dependencies/*.txt',
        'datatypes/converters/*.xml',
        'datatypes/set_metadata_tool.xml',
        'tools/imp_exp/imp_history_from_archive.xml',
        'tools/imp_exp/exp_history_to_archive.xml',
        # FIXME: web/proxy/js/lib doesn't exist
        #'web/proxy/js/*',
    ], 'tool_shed': [
        'galaxy_install/migrate/migrate.cfg',
        'scripts/bootstrap_tool_shed/parse_run_sh_args.sh',
        'scripts/bootstrap_tool_shed/bootstrap_tool_shed.sh',
        'scripts/bootstrap_tool_shed/user_info.xml',
    ]},
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
