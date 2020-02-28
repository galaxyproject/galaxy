import os
import pytest
import shutil
import ssl
import subprocess
import time

from irods.exception import CollectionDoesNotExist
from irods.exception import DataObjectDoesNotExist
from irods.session import iRODSSession

from galaxy.config import GalaxyAppConfiguration
from galaxy.objectstore.irods import IRODSObjectStore

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

CONFIG_DICT = {
    'auth': {
        'username': 'rods',
        'password': 'rods'
    },
    'resource': {
        'name': 'demoResc'
    },
    'zone': {
        'name': 'tempZone'
    },
    'connection': {
        'host': 'localhost',
        'port': '1247'
    },
    'cache': {
        'size': 1000.0, 
        'path': 'database/object_store_cache'
    },
    'extra_dirs': [{'type': 'job_work', 'path': 'database/job_working_directory_irods'}, {'type': 'temp', 'path': 'database/tmp_irods'}]
}

#class IrodsObjectStoreIntegrationTestCase(object):

#config = None 
#config_dict = None
#irods_os = None

@pytest.fixture(scope='module')
def setup_module():
    config = GalaxyAppConfiguration()

    config.object_store_cache_path = '/private/var/folders/pk/jwrvp5115zg81729h2x46f080000gn/T/tmpkffyrtx1/tmpb5xoh_67/tmp_ry_69z8/database/object_store_cache'
    config.file_path = '/private/var/folders/pk/jwrvp5115zg81729h2x46f080000gn/T/tmpkffyrtx1/tmpb5xoh_67/tmp_ry_69z8/database/objects'
    config.object_store_store_by = 'uuid'
    config.object_store_check_old_style = False
    config.jobs_directory = '/private/var/folders/pk/jwrvp5115zg81729h2x46f080000gn/T/tmpkffyrtx1/tmpb5xoh_67/tmp_ry_69z8/database/job_working_directory_k5dk3021'
    config.new_file_path = '/private/var/folders/pk/jwrvp5115zg81729h2x46f080000gn/T/tmpkffyrtx1/tmpb5xoh_67/tmp_ry_69z8/database/new_files_path_sej_tqh7'

    config_dict = CONFIG_DICT

    irods_os = IRODSObjectStore(config, CONFIG_DICT)
    return irods_os

#    @classmethod
#def teardown_module(module):
#     del irods_os
#     del config_dict
#     del config

def test_instantiate_irods(setup_module):
    print('**********************')
    print('setup_module.to_dict()')
    print(setup_module.to_dict())
    print('**********************')
    assert 1 == 1
