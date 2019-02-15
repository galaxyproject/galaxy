import os
import shutil
import tarfile
from shutil import rmtree
from tempfile import mkdtemp

from galaxy import model
from galaxy.exceptions import MalformedContents
from galaxy.tools.imp_exp import JobImportHistoryArchiveWrapper, unpack_tar_gz_archive
from galaxy.tools.imp_exp.export_history import create_archive
from ..unittest_utils.galaxy_mock import MockApp


# good enough for the very specific tests we're writing as of now...
DATASETS_ATTRS = '''[{{"info": "\\nuploaded txt file", "peek": "foo\\n\\n\\n\\n\\n\\n", "update_time": "2016-02-08 18:39:22.937474", "name": "Pasted Entry", "extension": "txt", "tags": {{}}, "__HistoryDatasetAssociation__": true, "file_name": "{file_name}", "deleted": false, "designation": null, "visible": true, "create_time": "2016-02-08 18:38:38.682087", "hid": 1, "parent_id": null, "extra_files_path": "", "uuid": "406d913e-925d-4ccd-800d-06c9b32df309", "metadata": {{"dbkey": "?", "data_lines": 1}}, "annotation": null, "blurb": "1 line", "exported": true}}]'''
DATASETS_ATTRS_PROVENANCE = '''[]'''
HISTORY_ATTRS = '''{"hid_counter": 2, "update_time": "2016-02-08 18:38:38.705058", "create_time": "2016-02-08 18:38:20.790057", "name": "paste", "tags": {}, "genome_build": "?", "annotation": null}'''
JOBS_ATTRS = '''[{"info": null, "tool_id": "upload1", "update_time": "2016-02-08T18:39:23.356482", "stdout": "", "input_mapping": {}, "tool_version": "1.1.4", "traceback": null, "command_line": "python /galaxy/tools/data_source/upload.py /galaxy /scratch/tmppwU9rD /scratch/tmpP4_45Y 1:/scratch/jobs/000/dataset_1_files:/data/000/dataset_1.dat", "exit_code": 0, "output_datasets": [1], "state": "ok", "create_time": "2016-02-08T18:38:39.153873", "params": {"files": [{"to_posix_lines": "Yes", "NAME": "None", "file_data": null, "space_to_tab": null, "url_paste": "/scratch/strio_url_paste_o6nrv8", "__index__": 0, "ftp_files": "", "uuid": "None"}], "paramfile": "/scratch/tmpP4_45Y", "file_type": "auto", "files_metadata": {"file_type": "auto", "__current_case__": 41}, "async_datasets": "None", "dbkey": "?"}, "stderr": ""}]'''


def _run_jihaw_cleanup(history_archive, msg):
    app = MockApp()
    job = model.Job()
    job.stderr = ''
    jiha = model.JobImportHistoryArchive(job=job, archive_dir=history_archive.arc_directory)
    app.model.context.current.add_all([job, jiha])
    app.model.context.flush()
    jihaw = JobImportHistoryArchiveWrapper(app, 1)  # yeehaw!
    try:
        jihaw.cleanup_after_job()
        data = app.object_store.get_data(model.Dataset(1))
        assert data != 'insecure', msg
    except MalformedContents:
        pass


def test_create_archive():
    tempdir = mkdtemp()
    dataset = os.path.join(tempdir, 'dataset_1.dat')
    history_attrs_file = os.path.join(tempdir, 'history_attrs_file.txt')
    datasets_attrs_file = os.path.join(tempdir, 'dataset_attrs_file.txt')
    jobs_attrs_file = os.path.join(tempdir, 'jobs_attrs_file.txt')
    out_file = os.path.join(tempdir, 'out.tar.gz')
    with open(dataset, 'w') as out:
        out.write('Hello\n')
    with open(history_attrs_file, 'w') as out:
        out.write(HISTORY_ATTRS)
    with open(datasets_attrs_file, 'w') as out:
        out.write(DATASETS_ATTRS.format(file_name=dataset))
    with open(jobs_attrs_file, 'w') as out:
        out.write(JOBS_ATTRS)
    try:
        create_archive(history_attrs_file, datasets_attrs_file, jobs_attrs_file, out_file, gzip=True)
        with tarfile.open(out_file) as t:
            assert t.getnames() == ['datasets/Pasted_Entry_1.txt', 'history_attrs.txt', 'datasets_attrs.txt', 'jobs_attrs.txt']
    finally:
        shutil.rmtree(tempdir)


def test_history_import_symlink():
    """ Ensure a history containing a dataset that is a symlink cannot be imported
    """
    with HistoryArchive() as history_archive:
        history_archive.write_metafiles()
        history_archive.write_link('datasets/Pasted_Entry_1.txt', '../target.txt')
        history_archive.write_file('target.txt', 'insecure')
        _run_jihaw_cleanup(history_archive, 'Symlink dataset in import archive allowed')


def test_history_import_relpath_in_metadata():
    """ Ensure that dataset_attrs.txt cannot contain a relative path outside the archive
    """
    with HistoryArchive() as history_archive:
        history_archive.write_metafiles(dataset_file_name='../outside.txt')
        history_archive.write_file('datasets/Pasted_Entry_1.txt', 'foo')
        history_archive.write_outside()
        _run_jihaw_cleanup(history_archive, 'Relative parent path in datasets_attrs.txt allowed')


def test_history_import_abspath_in_metadata():
    """ Ensure that dataset_attrs.txt cannot contain a absolute path outside the archive
    """
    with HistoryArchive() as history_archive:
        history_archive.write_metafiles(
            dataset_file_name=os.path.join(history_archive.temp_directory, 'outside.txt'))
        history_archive.write_file('datasets/Pasted_Entry_1.txt', 'foo')
        history_archive.write_outside()
        _run_jihaw_cleanup(history_archive, 'Absolute path in datasets_attrs.txt allowed')


def _run_unpack(history_archive, dest_parent, msg):
    dest_dir = os.path.join(dest_parent, 'dest')
    insecure_dir = os.path.join(dest_parent, 'insecure')
    os.makedirs(dest_dir)
    options = Dummy()
    options.is_url = False
    options.is_file = True
    options.is_b64encoded = False
    args = (history_archive.tar_file_path, dest_dir)
    try:
        unpack_tar_gz_archive.main(options, args)
    except AssertionError:
        pass
    assert not os.path.exists(insecure_dir), msg


def test_history_import_relpath_in_archive():
    """ Ensure that a history import archive cannot reference a relative path
    outside the archive
    """
    dest_parent = mkdtemp()
    with HistoryArchive(arcname_prefix='../insecure') as history_archive:
        history_archive.write_metafiles()
        history_archive.write_file('datasets/Pasted_Entry_1.txt', 'foo')
        history_archive.finalize()
        _run_unpack(history_archive, dest_parent, 'Relative parent path in import archive allowed')


def test_history_import_abspath_in_archive():
    """ Ensure that a history import archive cannot reference a absolute path
    outside the archive
    """
    dest_parent = mkdtemp()
    arcname_prefix = os.path.abspath(os.path.join(dest_parent, 'insecure'))
    with HistoryArchive(arcname_prefix=arcname_prefix) as history_archive:
        history_archive.write_metafiles()
        history_archive.write_file('datasets/Pasted_Entry_1.txt', 'foo')
        history_archive.finalize()
        _run_unpack(history_archive, dest_parent, 'Absolute path in import archive allowed')


class HistoryArchive(object):
    def __init__(self, arcname_prefix=None):
        self.temp_directory = mkdtemp()
        self.arc_directory = os.path.join(self.temp_directory, 'archive')
        self.arcname_prefix = arcname_prefix
        self.tar_file_path = os.path.join(self.temp_directory, 'archive.tar.gz')
        self.tar_file = tarfile.open(self.tar_file_path, 'w:gz')
        os.makedirs(self.arc_directory)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        rmtree(self.temp_directory)

    def _create_parent(self, fname):
        path = os.path.join(self.arc_directory, fname)
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

    def _arcname(self, path):
        if self.arcname_prefix:
            path = os.path.join(self.arcname_prefix, path)
        return path

    def write_metafiles(self, dataset_file_name='datasets/Pasted_Entry_1.txt'):
        self.write_file('datasets_attrs.txt',
                        DATASETS_ATTRS.format(file_name=dataset_file_name))
        self.write_file('datasets_attrs.txt.provenance', DATASETS_ATTRS_PROVENANCE)
        self.write_file('history_attrs.txt', HISTORY_ATTRS)
        self.write_file('jobs_attrs.txt', JOBS_ATTRS)

    def write_outside(self, fname='outside.txt', contents='invalid'):
        with open(os.path.join(self.temp_directory, fname), 'w') as f:
            f.write(contents)

    def write_file(self, fname, contents):
        self._create_parent(fname)
        path = os.path.join(self.arc_directory, fname)
        with open(path, 'w') as f:
            f.write(contents)
        # TarFile.add() (via TarFile.gettarinfo()) strips leading '/' and is
        # unsuitable for our purposes
        ti = self.tar_file.gettarinfo(fileobj=open(path, 'rb'))
        ti.name = self._arcname(fname)
        self.tar_file.addfile(ti, fileobj=open(path, 'rb'))

    def write_link(self, fname, target):
        self._create_parent(fname)
        path = os.path.join(self.arc_directory, fname)
        os.symlink(target, path)

    def finalize(self):
        self.tar_file.close()


class Dummy(object):
    pass
