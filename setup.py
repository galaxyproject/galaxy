from setuptools import setup, find_packages


readme = open('README.rst').read()
VERSION = None


# TODO: detect if we are not running from pip (inspect the stack?) and if not,
# suggest using `pip install -i https://wheels.galaxyproject.org/simple .`


# sets VERSION (also VERSION_MAJOR and VERSION_MINOR)
execfile('lib/galaxy/version.py')

# Note we really shouldn't do things this way, but it makes the most sense for now:
#   https://caremad.io/2013/07/setup-vs-requirement/
requirements = []
with open('requirements.txt') as fh:
    for line in fh:
        line = line.strip()
        if line.startswith('#') or line.startswith('-') or line == '':
            continue
        if '#' in line:
            line = line[:line.index('#')].strip()
        requirements.append(line)

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
        galaxy-config=galaxy.config.script:main
        galaxy-manage-db=galaxy.model.orm.scripts:manage_db
    ''',
    package_data={
        'galaxy': [
            'config/sample/*',
            'exceptions/error_codes.json',
            'datatypes/converters/*.xml',
            'datatypes/display_applications/configs/*/*.xml',
            'datatypes/set_metadata_tool.xml',
            'jobs/runners/util/job_script/DEFAULT_JOB_FILE_TEMPLATE.sh',
            'jobs/runners/util/job_script/CLUSTER_SLOTS_STATEMENT.sh',
            'tools/imp_exp/imp_history_from_archive.xml',
            'tools/imp_exp/exp_history_to_archive.xml',
            'model/migrate/migrate.cfg',
            'dependencies/*.txt',
            'util/docutils_template.txt',
        ],
        'tool_shed': [
            'galaxy_install/migrate/migrate.cfg',
            'galaxy_install/migrate/scripts/*',
            'scripts/bootstrap_tool_shed/parse_run_sh_args.sh',
            'scripts/bootstrap_tool_shed/bootstrap_tool_shed.sh',
            'scripts/bootstrap_tool_shed/user_info.xml',
        ],
    },
    package_dir={'': 'lib'},
    include_package_data=True,
    dependency_links=['https://wheels.galaxyproject.org/packages'],
    setup_requires=['pip>=8.1'],
    install_requires=requirements,
    extras_require={
        'postgresql': ['psycopg2==2.6.1'],
    },
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
