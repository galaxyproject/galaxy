import os
import pytest
import shutil
import ssl
import subprocess
import time

from irods.exception import CollectionDoesNotExist
from irods.exception import DataObjectDoesNotExist
from irods.session import iRODSSession

from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

class IrodsObjectStoreIntegrationTestCase(integration_util.IntegrationTestCase):

    container_name = "irods_server"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_config_file"] = "object_store_conf.xml" 

    @classmethod
    def setUpClass(cls):
        super(IrodsObjectStoreIntegrationTestCase, cls).setUpClass()
        IrodsObjectStoreIntegrationTestCase.start_irods_server(container_name=IrodsObjectStoreIntegrationTestCase.container_name)

        # Let the server start before running the test
        time.sleep(10)

    @classmethod
    def tearDownClass(cls): 
        super(IrodsObjectStoreIntegrationTestCase, cls).tearDownClass()
        IrodsObjectStoreIntegrationTestCase.stop_irods_server(container_name=IrodsObjectStoreIntegrationTestCase.container_name)       

    @classmethod
    def start_irods_server(cls, container_name, irods_port=1247, docker_image='kxk302/irods-server:0.1'):
        start_server = ['docker', 'run', '-h', 'localhost', '-p', '{port}:1247'.format(port=irods_port), '-d', '--name', container_name, docker_image]
        subprocess.check_call(start_server) 
        
    @classmethod
    def stop_irods_server(cls, container_name):
        subprocess.check_call(['docker', 'rm', '-f', container_name])

    def test_get_existing_collection(self):
        with iRODSSession(host='localhost', 
            port='1247', 
            user='rods',  
            password='rods', 
            zone='tempZone') as session:

            zone='tempZone'
            user='rods'
        
            aCollection = "/" + zone + "/home/" + user

            coll = session.collections.get(aCollection)
            assert coll.path == aCollection, "Error! Got wrong collection path"
            assert len(coll.subcollections) == 0, "Error! Collection should not have any subcollections!"
            assert len(coll.data_objects) == 0, "Error! Collection should not have any data objects!"

    def test_create_delete_new_collection(self):
        with iRODSSession(host='localhost', 
            port='1247', 
            user='rods',  
            password='rods', 
            zone='tempZone') as session:

            zone='tempZone'
            user='rods'

            newCollection = "/" + zone + "/home/" + user + "/testdir"
    
            coll = session.collections.create(newCollection)
            assert coll.path == newCollection, "Error! Got wrong collection path"
            assert len(coll.subcollections) == 0, "Error! Collection should not have any subcollections!"
            assert len(coll.data_objects) == 0, "Error! Collection should not have any data objects!" 

            coll.remove(recurse=True, force=True)

            with pytest.raises(CollectionDoesNotExist):
                coll = session.collections.get(newCollection)

    def test_create_delete_new_data_object(self):
        with iRODSSession(host='localhost', 
            port='1247', 
            user='rods',  
            password='rods', 
            zone='tempZone') as session:

            zone='tempZone'
            user='rods'
     
            newCollection = "/" + zone + "/home/" + user + "/testdir"
            newDataObject = newCollection + "/testDataObject"

            # Create new collection
            coll = session.collections.create(newCollection)
            assert coll.path == newCollection, "Error! Got wrong collection path"
            assert len(coll.subcollections) == 0, "Error! Collection should not have any subcollections!"
            assert len(coll.data_objects) == 0, "Error! Collection should not have any data objects!"

            # Create data object
            obj = session.data_objects.create(newDataObject)
            assert obj.name == "testDataObject", "Error! Got wrong data object"

            # Delete data object
            obj.unlink(force=True)

            # Get data object
            with pytest.raises(DataObjectDoesNotExist):
                obj = session.data_objects.get(newDataObject)

            # Delete collection
            coll.remove(recurse=True, force=True)

            with pytest.raises(CollectionDoesNotExist):
                coll = session.collections.get(newCollection)
 
    def test_populate_fetch_new_data_object(self):
        with iRODSSession(host='localhost', 
            port='1247', 
            user='rods',  
            password='rods', 
            zone='tempZone') as session:

            zone='tempZone'
            user='rods'

            newCollection = "/" + zone + "/home/" + user + "/testdir"
            fileName = "irods_beginner_training_2016.pdf"
            fileNamePath = os.path.join(SCRIPT_DIRECTORY, fileName)
            backupFileName = "irods_beginner_training_2016_backup.pdf"
            backupFileNamePath = os.path.join(SCRIPT_DIRECTORY, backupFileName)
 
            # Copy file from backup
            shutil.copyfile(fileNamePath, backupFileNamePath)

            # Create new collection 
            coll = session.collections.create(newCollection)
            assert coll.path == newCollection, "Error! Got wrong collection path"
            assert len(coll.subcollections) == 0, "Error! Collection should not have any subcollections!"
            assert len(coll.data_objects) == 0, "Error! Collection should not have any data objects!" 

            # Create new data object
            session.data_objects.put(backupFileNamePath, newCollection + "/" + backupFileName)
    
            # Delete local file
            os.remove(backupFileNamePath)         
    
            # Get the data object back
            obj = session.data_objects.get(newCollection + "/" + backupFileName)
    
            # Write the data object to the file system
            with obj.open("r") as f_in, open(backupFileNamePath, "wb") as f_out:
                f_out.write(f_in.read())
    
            # Assert the size of file fetched from iRODS matches the local backup copy
            assert os.path.getsize(fileNamePath) == os.path.getsize(backupFileNamePath), "Error! Size of file fetched from iRODS does not match the size of the original file" 
    
            # Delete local file
            os.remove(backupFileNamePath)         
    
            # Delete data object
            obj.unlink(force=True)
    
            # Get data object
            with pytest.raises(DataObjectDoesNotExist):
                obj = session.data_objects.get(newCollection + "/" + backupFileName)
    
            # Delete collection
            coll.remove(recurse=True, force=True)
    
            # Get collection
            with pytest.raises(CollectionDoesNotExist):
                coll = session.collections.get(newCollection)
