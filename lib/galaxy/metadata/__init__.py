"""Define abstraction for capturing the metadata of job's output datasets."""

import abc
import json
import os
import shutil
import tempfile
from logging import getLogger
from os.path import abspath

import six
from six.moves import cPickle

import galaxy.model
from galaxy.model.metadata import FileParameter, MetadataTempFile
from galaxy.util import in_directory

log = getLogger(__name__)

SET_METADATA_SCRIPT = 'from galaxy_ext.metadata.set_metadata import set_metadata; set_metadata()'


def get_metadata_compute_strategy(app, job_id):
    metadata_strategy = app.config.metadata_strategy
    if metadata_strategy == "legacy":
        return JobExternalOutputMetadataWrapper(job_id)
    else:
        return PortableDirectoryMetadataGenerator(job_id)


@six.add_metaclass(abc.ABCMeta)
class MetadataCollectionStrategy(object):
    """Interface describing the abstract process of writing out and collecting output metadata.
    """

    def invalidate_external_metadata(self, datasets, sa_session):
        """Invalidate written files."""
        pass

    def set_job_runner_external_pid(self, pid, sa_session):
        pass

    def cleanup_external_metadata(self, sa_session):
        pass

    @abc.abstractmethod
    def setup_external_metadata(self, datasets_dict, sa_session, exec_dir=None,
                                tmp_dir=None, dataset_files_path=None,
                                output_fnames=None, config_root=None,
                                config_file=None, datatypes_config=None,
                                job_metadata=None, compute_tmp_dir=None,
                                include_command=True, max_metadata_value_size=0,
                                kwds=None):
        """Setup files needed for external metadata collection.

        If include_command is True, return full Python command to externally compute metadata
        otherwise just the arguments to galaxy_ext.metadata.set_metadata required to build.
        """

    @abc.abstractmethod
    def external_metadata_set_successfully(self, dataset, name, sa_session, working_directory):
        """Return boolean indicating if metadata for specified dataset was written properly."""

    @abc.abstractmethod
    def load_metadata(self, dataset, name, sa_session, working_directory, remote_metadata_directory=None):
        """Load metadata calculated externally into specified dataset."""

    def _load_metadata_from_path(self, dataset, metadata_output_path, working_directory, remote_metadata_directory):

        def path_rewriter(path):
            if not path:
                return path
            normalized_remote_metadata_directory = remote_metadata_directory and os.path.normpath(remote_metadata_directory)
            normalized_path = os.path.normpath(path)
            if remote_metadata_directory and normalized_path.startswith(normalized_remote_metadata_directory):
                return normalized_path.replace(normalized_remote_metadata_directory, working_directory, 1)
            return path

        dataset.metadata.from_JSON_dict(metadata_output_path, path_rewriter=path_rewriter)

    def _metadata_results_from_file(self, dataset, filename_results_code):
        with open(filename_results_code, "r") as f:
            rval, rstring = json.load(f)

        if not rval:
            log.debug('setting metadata externally failed for %s %s: %s' % (dataset.__class__.__name__, dataset.id, rstring))
        return rval


class PortableDirectoryMetadataGenerator(MetadataCollectionStrategy):

    def __init__(self, job_id):
        self.job_id = job_id

    def setup_external_metadata(self, datasets_dict, sa_session, exec_dir=None,
                                tmp_dir=None, dataset_files_path=None,
                                output_fnames=None, config_root=None,
                                config_file=None, datatypes_config=None,
                                job_metadata=None, compute_tmp_dir=None,
                                include_command=True, max_metadata_value_size=0,
                                kwds=None):
        assert job_metadata, "setup_external_metadata must be supplied with job_metadata path"
        kwds = kwds or {}
        tmp_dir = _init_tmp_dir(tmp_dir)

        metadata_dir = os.path.join(tmp_dir, "metadata")
        os.mkdir(metadata_dir)

        def job_relative_path(path):
            path_relative = os.path.relpath(path, tmp_dir)
            return path_relative

        outputs = {}

        for name, dataset in datasets_dict.items():
            assert name is not None
            assert name not in outputs

            key = name

            def _metadata_path(what):
                return os.path.join(metadata_dir, "metadata_%s_%s" % (what, key))

            _initialize_metadata_inputs(dataset, _metadata_path, tmp_dir, kwds)

            outputs[name] = {
                "filename_override": _get_filename_override(output_fnames, dataset.file_name)
            }

        metadata_params_path = os.path.join(metadata_dir, "params.json")
        metadata_params = {
            "job_metadata": job_relative_path(job_metadata),
            "datatypes_config": datatypes_config,
            "max_metadata_value_size": max_metadata_value_size,
            "outputs": outputs,
            "object_store_store_by": galaxy.model.Dataset.object_store.store_by,
        }
        with open(metadata_params_path, "w") as f:
            json.dump(metadata_params, f)

        if include_command:
            # return command required to build
            script_path = os.path.join(metadata_dir, "set.py")
            with open(script_path, "w") as f:
                f.write(SET_METADATA_SCRIPT)
            return 'pwd; python "metadata/set.py"'
        else:
            # return args to galaxy_ext.metadata.set_metadata required to build
            return ''

    def load_metadata(self, dataset, name, sa_session, working_directory, remote_metadata_directory=None):
        metadata_output_path = os.path.join(working_directory, "metadata", "metadata_out_%s" % name)
        self._load_metadata_from_path(dataset, metadata_output_path, working_directory, remote_metadata_directory)

    def external_metadata_set_successfully(self, dataset, name, sa_session, working_directory):
        metadata_results_path = os.path.join(working_directory, "metadata", "metadata_results_%s" % name)
        try:
            return self._metadata_results_from_file(dataset, metadata_results_path)
        except Exception:
            # if configured we need to try setting metadata internally
            return False


class JobExternalOutputMetadataWrapper(MetadataCollectionStrategy):
    """
    Class with methods allowing set_meta() to be called externally to the
    Galaxy head.
    This class allows access to external metadata filenames for all outputs
    associated with a job.
    We will use JSON as the medium of exchange of information, except for the
    DatasetInstance object which will use pickle (in the future this could be
    JSONified as well)
    """

    def __init__(self, job_id):
        self.job_id = job_id

    def _get_output_filenames_by_dataset(self, dataset, sa_session):
        if isinstance(dataset, galaxy.model.HistoryDatasetAssociation):
            return sa_session.query(galaxy.model.JobExternalOutputMetadata) \
                             .filter_by(job_id=self.job_id,
                                        history_dataset_association_id=dataset.id,
                                        is_valid=True) \
                             .first()  # there should only be one or None
        elif isinstance(dataset, galaxy.model.LibraryDatasetDatasetAssociation):
            return sa_session.query(galaxy.model.JobExternalOutputMetadata) \
                             .filter_by(job_id=self.job_id,
                                        library_dataset_dataset_association_id=dataset.id,
                                        is_valid=True) \
                             .first()  # there should only be one or None
        return None

    def _get_dataset_metadata_key(self, dataset):
        # Set meta can be called on library items and history items,
        # need to make different keys for them, since ids can overlap
        return "%s_%d" % (dataset.__class__.__name__, dataset.id)

    def invalidate_external_metadata(self, datasets, sa_session):
        for dataset in datasets:
            jeom = self._get_output_filenames_by_dataset(dataset, sa_session)
            # shouldn't be more than one valid, but you never know
            while jeom:
                jeom.is_valid = False
                sa_session.add(jeom)
                sa_session.flush()
                jeom = self._get_output_filenames_by_dataset(dataset, sa_session)

    def setup_external_metadata(self, datasets_dict, sa_session, exec_dir=None,
                                tmp_dir=None, dataset_files_path=None,
                                output_fnames=None, config_root=None,
                                config_file=None, datatypes_config=None,
                                job_metadata=None, compute_tmp_dir=None,
                                include_command=True, max_metadata_value_size=0,
                                kwds=None):
        kwds = kwds or {}
        tmp_dir = _init_tmp_dir(tmp_dir)
        _assert_datatypes_config(datatypes_config)

        # path is calculated for Galaxy, may be different on compute - rewrite
        # for the compute server.
        def metadata_path_on_compute(path):
            compute_path = path
            if compute_tmp_dir and tmp_dir and in_directory(path, tmp_dir):
                path_relative = os.path.relpath(path, tmp_dir)
                compute_path = os.path.join(compute_tmp_dir, path_relative)
            return compute_path

        # fill in metadata_files_dict and return the command with args required to set metadata
        def __metadata_files_list_to_cmd_line(metadata_files):
            line = '"%s,%s,%s,%s,%s,%s"' % (
                metadata_path_on_compute(metadata_files.filename_in),
                metadata_path_on_compute(metadata_files.filename_kwds),
                metadata_path_on_compute(metadata_files.filename_out),
                metadata_path_on_compute(metadata_files.filename_results_code),
                _get_filename_override(output_fnames, metadata_files.dataset.file_name),
                metadata_path_on_compute(metadata_files.filename_override_metadata),
            )
            return line

        datasets = list(datasets_dict.values())
        if exec_dir is None:
            exec_dir = os.path.abspath(os.getcwd())
        if dataset_files_path is None:
            dataset_files_path = galaxy.model.Dataset.file_path
        if config_root is None:
            config_root = os.path.abspath(os.getcwd())
        metadata_files_list = []
        for dataset in datasets:
            key = self._get_dataset_metadata_key(dataset)
            # future note:
            # wonkiness in job execution causes build command line to be called more than once
            # when setting metadata externally, via 'auto-detect' button in edit attributes, etc.,
            # we don't want to overwrite (losing the ability to cleanup) our existing dataset keys and files,
            # so we will only populate the dictionary once
            metadata_files = self._get_output_filenames_by_dataset(dataset, sa_session)
            if not metadata_files:
                job = sa_session.query(galaxy.model.Job).get(self.job_id)
                metadata_files = galaxy.model.JobExternalOutputMetadata(job=job, dataset=dataset)
                # we are using tempfile to create unique filenames, tempfile always returns an absolute path
                # we will use pathnames relative to the galaxy root, to accommodate instances where the galaxy root
                # is located differently, i.e. on a cluster node with a different filesystem structure

                def _metadata_path(what):
                    return abspath(tempfile.NamedTemporaryFile(dir=tmp_dir, prefix="metadata_%s_%s_" % (what, key)).name)

                filename_in, filename_out, filename_results_code, filename_kwds, filename_override_metadata = _initialize_metadata_inputs(dataset, _metadata_path, tmp_dir, kwds)

                # file to store existing dataset
                metadata_files.filename_in = filename_in

                # file to store metadata results of set_meta()
                metadata_files.filename_out = filename_out

                # file to store a 'return code' indicating the results of the set_meta() call
                # results code is like (True/False - if setting metadata was successful/failed , exception or string of reason of success/failure )
                metadata_files.filename_results_code = filename_results_code

                # file to store kwds passed to set_meta()
                metadata_files.filename_kwds = filename_kwds

                # existing metadata file parameters need to be overridden with cluster-writable file locations
                metadata_files.filename_override_metadata = filename_override_metadata

                # add to session and flush
                sa_session.add(metadata_files)
                sa_session.flush()
            metadata_files_list.append(metadata_files)
        args = '"%s" "%s" %s %s' % (metadata_path_on_compute(datatypes_config),
                                    job_metadata,
                                    " ".join(map(__metadata_files_list_to_cmd_line, metadata_files_list)),
                                    max_metadata_value_size)
        if include_command:
            # return command required to build
            fd, fp = tempfile.mkstemp(suffix='.py', dir=tmp_dir, prefix="set_metadata_")
            metadata_script_file = abspath(fp)
            with os.fdopen(fd, 'w') as f:
                f.write(SET_METADATA_SCRIPT)
            return 'python "%s" %s' % (metadata_path_on_compute(metadata_script_file), args)
        else:
            # return args to galaxy_ext.metadata.set_metadata required to build
            return args

    def external_metadata_set_successfully(self, dataset, name, sa_session, working_directory):
        metadata_files = self._get_output_filenames_by_dataset(dataset, sa_session)
        if not metadata_files:
            return False  # this file doesn't exist
        return self._metadata_results_from_file(dataset, metadata_files.filename_results_code)

    def cleanup_external_metadata(self, sa_session):
        log.debug('Cleaning up external metadata files')
        for metadata_files in sa_session.query(galaxy.model.Job).get(self.job_id).external_output_metadata:
            # we need to confirm that any MetadataTempFile files were removed, if not we need to remove them
            # can occur if the job was stopped before completion, but a MetadataTempFile is used in the set_meta
            MetadataTempFile.cleanup_from_JSON_dict_filename(metadata_files.filename_out)
            dataset_key = self._get_dataset_metadata_key(metadata_files.dataset)
            for key, fname in [('filename_in', metadata_files.filename_in),
                               ('filename_out', metadata_files.filename_out),
                               ('filename_results_code', metadata_files.filename_results_code),
                               ('filename_kwds', metadata_files.filename_kwds),
                               ('filename_override_metadata', metadata_files.filename_override_metadata)]:
                try:
                    os.remove(fname)
                except Exception as e:
                    log.debug('Failed to cleanup external metadata file (%s) for %s: %s' % (key, dataset_key, e))

    def set_job_runner_external_pid(self, pid, sa_session):
        for metadata_files in sa_session.query(galaxy.model.Job).get(self.job_id).external_output_metadata:
            metadata_files.job_runner_external_pid = pid
            sa_session.add(metadata_files)
            sa_session.flush()

    def load_metadata(self, dataset, name, sa_session, working_directory, remote_metadata_directory=None):
        # load metadata from file
        # we need to no longer allow metadata to be edited while the job is still running,
        # since if it is edited, the metadata changed on the running output will no longer match
        # the metadata that was stored to disk for use via the external process,
        # and the changes made by the user will be lost, without warning or notice
        output_filename = self._get_output_filenames_by_dataset(dataset, sa_session).filename_out
        self._load_metadata_from_path(dataset, output_filename, working_directory, remote_metadata_directory)


def _initialize_metadata_inputs(dataset, path_for_part, tmp_dir, kwds):
    filename_in = path_for_part("in")
    filename_out = path_for_part("out")
    filename_results_code = path_for_part("results")
    filename_kwds = path_for_part("kwds")
    filename_override_metadata = path_for_part("override")

    _dump_dataset_instance_to(dataset, filename_in)
    open(filename_out, 'wt+')  # create the file on disk, so it cannot be reused by tempfile (unlikely, but possible)
    # create the file on disk, so it cannot be reused by tempfile (unlikely, but possible)
    json.dump((False, 'External set_meta() not called'), open(filename_results_code, 'wt+'))
    json.dump(kwds, open(filename_kwds, 'wt+'), ensure_ascii=True)

    override_metadata = []
    for meta_key, spec_value in dataset.metadata.spec.items():
        if isinstance(spec_value.param, FileParameter) and dataset.metadata.get(meta_key, None) is not None:
            metadata_temp = MetadataTempFile()
            metadata_temp.tmp_dir = tmp_dir
            shutil.copy(dataset.metadata.get(meta_key, None).file_name, metadata_temp.file_name)
            override_metadata.append((meta_key, metadata_temp.to_JSON()))
    json.dump(override_metadata, open(filename_override_metadata, 'wt+'))

    return filename_in, filename_out, filename_results_code, filename_kwds, filename_override_metadata


def _assert_datatypes_config(datatypes_config):
    if datatypes_config is None:
        raise Exception('In setup_external_metadata, the received datatypes_config is None.')


def _dump_dataset_instance_to(dataset_instance, file_path):
    # FIXME: HACK
    # sqlalchemy introduced 'expire_on_commit' flag for sessionmaker at version 0.5x
    # This may be causing the dataset attribute of the dataset_association object to no-longer be loaded into memory when needed for pickling.
    # For now, we'll simply 'touch' dataset_association.dataset to force it back into memory.
    dataset_instance.dataset  # force dataset_association.dataset to be loaded before pickling
    # A better fix could be setting 'expire_on_commit=False' on the session, or modifying where commits occur, or ?

    # Touch also deferred column
    dataset_instance._metadata

    cPickle.dump(dataset_instance, open(file_path, 'wb+'))


def _get_filename_override(output_fnames, file_name):
    if output_fnames:
        for dataset_path in output_fnames:
            if dataset_path.real_path == file_name:
                return dataset_path.false_path or dataset_path.real_path
    return ""


def _init_tmp_dir(tmp_dir):
    assert tmp_dir is not None

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    return tmp_dir
