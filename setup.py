from setuptools import setup, find_packages


readme = open('README.rst').read()
VERSION = None


# TODO: detect if we are not running from pip (inspect the stack?) and if not,
# suggest using `pip install -i https://wheels.galaxyproject.org/simple .`


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
        galaxy-config=galaxy.config.script:main
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
    # FIXME: read requirements.txt into a list...
    install_requires=[
        'bx-python==0.7.3',
        'MarkupSafe==0.23',
        'PyYAML==3.11',
        'SQLAlchemy==1.0.8',
        'mercurial==3.7.3',
        'numpy==1.9.2',
        'pycrypto==2.6.1',
        'Paste==2.0.2',
        'PasteDeploy==1.5.2',
        'docutils==0.12',
        'wchartype==0.1',
        'repoze.lru==0.6',
        'Routes==2.2',
        'WebOb==1.4.1',
        'WebHelpers==1.3',
        'Mako==1.0.2',
        'pytz==2015.4',
        'Babel==2.0',
        'Beaker==1.7.0',
        'dictobj==0.3.1',
        'nose==1.3.7',
        'Parsley==1.3',
        'six==1.9.0',
        'Whoosh==2.7.4',
        'Cheetah==2.4.4',
        'Markdown==2.6.3',
        'bioblend==0.7.0',
        'boto==2.38.0',
        'requests==2.8.1',
        'requests-toolbelt==0.4.0',
        'kombu==3.0.30',
        'amqp==1.4.8',
        'anyjson==0.3.3',
        'psutil==4.1.0',
        'pulsar-galaxy-lib==0.7.0.dev4',
        'sqlalchemy-migrate==0.10.0',
        'decorator==4.0.2',
        'Tempita==0.5.3dev',
        'sqlparse==0.1.16',
        'pbr==1.8.0',
        'svgwrite==1.1.6',
        'pyparsing==2.1.1',
        'Fabric==1.10.2',
        'paramiko==1.15.2',
        'ecdsa==0.13',
        'pysam==0.8.4+gx1',
    ],
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
