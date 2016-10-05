import os

from contextlib import contextmanager
from shutil import rmtree
from string import Template
from tempfile import mkdtemp

from galaxy import objectstore
from galaxy.exceptions import ObjectInvalid

DISK_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="disk">
    <files_dir path="${temp_directory}/files1"/>
    <extra_dir type="temp" path="${temp_directory}/tmp1"/>
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
</object_store>
"""


def test_disk_store():
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        # Test no dataset with id 1 exists.
        absent_dataset = MockDataset(1)
        assert not object_store.exists(absent_dataset)

        # Write empty dataset 2 in second backend, ensure it is empty and
        # exists.
        empty_dataset = MockDataset(2)
        directory.write("", "files1/000/dataset_2.dat")
        assert object_store.exists(empty_dataset)
        assert object_store.empty(empty_dataset)

        # Write non-empty dataset in backend 1, test it is not emtpy & exists.
        hello_world_dataset = MockDataset(3)
        directory.write("Hello World!", "files1/000/dataset_3.dat")
        assert object_store.exists(hello_world_dataset)
        assert not object_store.empty(hello_world_dataset)

        # Test get_data
        data = object_store.get_data(hello_world_dataset)
        assert data == "Hello World!"

        data = object_store.get_data(hello_world_dataset, start=1, count=6)
        assert data == "ello W"

        # Test Size

        # Test absent and empty datasets yield size of 0.
        assert object_store.size(absent_dataset) == 0
        assert object_store.size(empty_dataset) == 0
        # Elsewise
        assert object_store.size(hello_world_dataset) > 0  # Should this always be the number of bytes?

        # Test percent used (to some degree)
        percent_store_used = object_store.get_store_usage_percent()
        assert percent_store_used > 0.0
        assert percent_store_used < 100.0

        # Test update_from_file test
        output_dataset = MockDataset(4)
        output_real_path = os.path.join(directory.temp_directory, "files1", "000", "dataset_4.dat")
        assert not os.path.exists(output_real_path)
        output_working_path = directory.write("NEW CONTENTS", "job_working_directory1/example_output")
        object_store.update_from_file(output_dataset, file_name=output_working_path, create=True)
        assert os.path.exists(output_real_path)

        # Test delete
        to_delete_dataset = MockDataset(5)
        to_delete_real_path = directory.write("content to be deleted!", "files1/000/dataset_5.dat")
        assert object_store.exists(to_delete_dataset)
        assert object_store.delete(to_delete_dataset)
        assert not object_store.exists(to_delete_dataset)
        assert not os.path.exists(to_delete_real_path)


def test_disk_store_alt_name_relpath():
    """ Test that alt_name cannot be used to access arbitrary paths using a
    relative path
    """
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        empty_dataset = MockDataset(1)
        directory.write("", "files1/000/dataset_1.dat")
        directory.write("foo", "foo.txt")
        try:
            assert object_store.get_data(
                empty_dataset,
                extra_dir='dataset_1_files',
                alt_name='../../../foo.txt') != 'foo'
        except ObjectInvalid:
            pass


def test_disk_store_alt_name_abspath():
    """ Test that alt_name cannot be used to access arbitrary paths using a
    absolute path
    """
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        empty_dataset = MockDataset(1)
        directory.write("", "files1/000/dataset_1.dat")
        absfoo = os.path.abspath(os.path.join(directory.temp_directory, "foo.txt"))
        with open(absfoo, 'w') as f:
            f.write("foo")
        try:
            assert object_store.get_data(
                empty_dataset,
                extra_dir='dataset_1_files',
                alt_name=absfoo) != 'foo'
        except ObjectInvalid:
            pass


HIERARCHICAL_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="hierarchical">
    <backends>
        <backend id="files1" type="disk" weight="1" order="0">
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1" order="1">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""


def test_hierarchical_store():
    with TestConfig(HIERARCHICAL_TEST_CONFIG) as (directory, object_store):

        # Test no dataset with id 1 exists.
        assert not object_store.exists(MockDataset(1))

        # Write empty dataset 2 in second backend, ensure it is empty and
        # exists.
        directory.write("", "files2/000/dataset_2.dat")
        assert object_store.exists(MockDataset(2))
        assert object_store.empty(MockDataset(2))

        # Write non-empty dataset in backend 1, test it is not emtpy & exists.
        directory.write("Hello World!", "files1/000/dataset_3.dat")
        assert object_store.exists(MockDataset(3))
        assert not object_store.empty(MockDataset(3))

        # Assert creation always happens in first backend.
        for i in range(100):
            dataset = MockDataset(100 + i)
            object_store.create(dataset)
            assert object_store.get_filename(dataset).find("files1") > 0


DISTRIBUTED_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="distributed">
    <backends>
        <backend id="files1" type="disk" weight="2" order="0">
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1" order="1">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""


def test_distributed_store():
    with TestConfig(DISTRIBUTED_TEST_CONFIG) as (directory, object_store):
        with __stubbed_persistence() as persisted_ids:
            for i in range(100):
                dataset = MockDataset(100 + i)
                object_store.create(dataset)

        # Test distributes datasets between backends according to weights
        backend_1_count = len([v for v in persisted_ids.values() if v == "files1"])
        backend_2_count = len([v for v in persisted_ids.values() if v == "files2"])

        assert backend_1_count > 0
        assert backend_2_count > 0
        assert backend_1_count > backend_2_count


class TestConfig(object):
    def __init__(self, config_xml):
        self.temp_directory = mkdtemp()
        self.write(config_xml, "store.xml")
        config = MockConfig(self.temp_directory)
        self.object_store = objectstore.build_object_store_from_config(config)

    def __enter__(self):
        return self, self.object_store

    def __exit__(self, type, value, tb):
        rmtree(self.temp_directory)

    def write(self, contents, name):
        path = os.path.join(self.temp_directory, name)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        contents_template = Template(contents)
        expanded_contents = contents_template.safe_substitute(temp_directory=self.temp_directory)
        open(path, "w").write(expanded_contents)
        return path


class MockConfig(object):

    def __init__(self, temp_directory):
        self.file_path = temp_directory
        self.object_store_config_file = os.path.join(temp_directory, "store.xml")
        self.object_store_check_old_style = False
        self.jobs_directory = temp_directory
        self.new_file_path = temp_directory
        self.umask = 0000


class MockDataset(object):

    def __init__(self, id):
        self.id = id
        self.object_store_id = None


# Poor man's mocking. Need to get a real mocking library as real Galaxy development
# dependnecy.
PERSIST_METHOD_NAME = "_create_object_in_session"


@contextmanager
def __stubbed_persistence():
    real_method = getattr(objectstore, PERSIST_METHOD_NAME)
    try:
        persisted_ids = {}

        def persist(object):
            persisted_ids[object.id] = object.object_store_id
        setattr(objectstore, PERSIST_METHOD_NAME, persist)
        yield persisted_ids

    finally:
        setattr(objectstore, PERSIST_METHOD_NAME, real_method)
