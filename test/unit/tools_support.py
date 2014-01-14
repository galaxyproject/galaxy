""" Module contains test fixtures meant to aide in the testing of jobs and
tool evaluation. Such extensive "fixtures" are something of an anti-pattern
so use of this should be limitted to tests of very 'extensive' classes.
"""

from collections import defaultdict
import os.path
import tempfile
import shutil

from galaxy.util.bunch import Bunch
import galaxy.model
from galaxy.model import mapping


class UsesApp( object ):

    def setup_app( self ):
        # The following line is needed in order to create
        # HistoryDatasetAssociations - ideally the model classes would be
        # usable without the ORM infrastructure in place.
        mapping.init( "/tmp", "sqlite:///:memory:", create_tables=True )
        self.test_directory = tempfile.mkdtemp()
        self.app = MockApp(self.test_directory)

    def tear_down_app( self ):
        shutil.rmtree( self.test_directory )


class MockApp( object ):

    def __init__( self, test_directory ):

        self.datatypes_registry = Bunch(
            integrated_datatypes_configs='/galaxy/integrated_datatypes_configs.xml',
            get_datatype_by_extension=lambda ext: Bunch(),
        )

        self.config = Bunch(
            outputs_to_working_directory=False,
            new_file_path=os.path.join(test_directory, "new_files"),
            tool_data_path=os.path.join(test_directory, "tools"),
            root=os.path.join(test_directory, "galaxy"),
            admin_users="mary@example.com",
        )

        # Setup some attributes for downstream extension by specific tests.
        self.job_config = Bunch()
        # Create self.model to mimic app.model.
        self.model = Bunch( context=MockContext() )
        for module_member_name in dir( galaxy.model ):
            module_member = getattr(galaxy.model, module_member_name)
            if type( module_member ) == type:
                self.model[ module_member_name ] = module_member
        self.toolbox = None
        self.object_store = None


class MockContext(object):

    def __init__(self, model_objects=None):
        self.expunged_all = False
        self.flushed = False
        self.model_objects = model_objects or defaultdict( lambda: {} )
        self.created_objects = []

    def expunge_all(self):
        self.expunged_all = True

    def query(self, clazz):
        return MockQuery(self.model_objects.get(clazz))

    def flush(self):
        self.flushed = True

    def add(self, object):
        self.created_objects.append(object)


class MockQuery(object):

    def __init__(self, class_objects):
        self.class_objects = class_objects

    def filter_by(self, **kwds):
        return Bunch(first=lambda: None)

    def get(self, id):
        return self.class_objects.get(id, None)


__all__ = [ UsesApp ]
