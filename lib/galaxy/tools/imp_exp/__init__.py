import datetime
import json
import logging
import os
import shutil
import tempfile
from json import dumps, load

from sqlalchemy.orm import eagerload_all
from sqlalchemy.sql import expression


from galaxy import model
from galaxy.exceptions import MalformedContents
from galaxy.exceptions import ObjectNotFound
from galaxy.model.item_attrs import add_item_annotation, get_item_annotation_str
from galaxy.util import unicodify
from galaxy.version import VERSION_MAJOR

log = logging.getLogger(__name__)

ATTRS_FILENAME_HISTORY = 'history_attrs.txt'
ATTRS_FILENAME_DATASETS = 'datasets_attrs.txt'
ATTRS_FILENAME_JOBS = 'jobs_attrs.txt'


class JobImportHistoryArchiveWrapper:
    """
        Class provides support for performing jobs that import a history from
        an archive.
    """

    def __init__(self, app, job_id):
        self.app = app
        self.job_id = job_id
        self.sa_session = self.app.model.context

    def cleanup_after_job(self):
        """ Set history, datasets, and jobs' attributes and clean up archive directory. """

        def file_in_dir(file_path, a_dir):
            """ Returns true if file is in directory. """
            abs_file_path = os.path.abspath(file_path)
            return os.path.split(abs_file_path)[0] == a_dir

        #
        # Import history.
        #

        jiha = self.sa_session.query(model.JobImportHistoryArchive).filter_by(job_id=self.job_id).first()
        if jiha:
            try:
                archive_dir = jiha.archive_dir
                archive_dir = os.path.realpath(archive_dir)
                user = jiha.job.user

                # Bioblend previous to 17.01 exported histories with an extra subdir.
                if not os.path.exists(os.path.join(archive_dir, ATTRS_FILENAME_HISTORY)):
                    for d in os.listdir(archive_dir):
                        if os.path.isdir(os.path.join(archive_dir, d)):
                            archive_dir = os.path.join(archive_dir, d)
                            break

                #
                # Create history.
                #
                history_attr_file_name = os.path.join(archive_dir, ATTRS_FILENAME_HISTORY)
                history_attrs = load(open(history_attr_file_name))

                # Create history.
                new_history = model.History(name='imported from archive: %s' % history_attrs['name'],
                                            user=user)
                new_history.importing = True
                new_history.hid_counter = history_attrs['hid_counter']
                new_history.genome_build = history_attrs['genome_build']
                self.sa_session.add(new_history)
                jiha.history = new_history
                self.sa_session.flush()

                # Add annotation, tags.
                if user:
                    add_item_annotation(self.sa_session, user, new_history, history_attrs['annotation'])
                    """
                    TODO: figure out to how add tags to item.
                    for tag, value in history_attrs[ 'tags' ].items():
                        trans.app.tag_handler.apply_item_tags( trans, trans.user, new_history, get_tag_str( tag, value ) )
                    """

                #
                # Create datasets.
                #
                datasets_attrs_file_name = os.path.join(archive_dir, ATTRS_FILENAME_DATASETS)
                datasets_attrs = load(open(datasets_attrs_file_name))
                provenance_file_name = datasets_attrs_file_name + ".provenance"

                if os.path.exists(provenance_file_name):
                    provenance_attrs = load(open(provenance_file_name))
                    datasets_attrs += provenance_attrs

                # Create datasets.
                for dataset_attrs in datasets_attrs:
                    metadata = dataset_attrs['metadata']

                    # Create dataset and HDA.
                    hda = model.HistoryDatasetAssociation(name=dataset_attrs['name'],
                                                          extension=dataset_attrs['extension'],
                                                          info=dataset_attrs['info'],
                                                          blurb=dataset_attrs['blurb'],
                                                          peek=dataset_attrs['peek'],
                                                          designation=dataset_attrs['designation'],
                                                          visible=dataset_attrs['visible'],
                                                          dbkey=metadata['dbkey'],
                                                          metadata=metadata,
                                                          history=new_history,
                                                          create_dataset=True,
                                                          sa_session=self.sa_session)
                    if 'uuid' in dataset_attrs:
                        hda.dataset.uuid = dataset_attrs["uuid"]
                    if dataset_attrs.get('exported', True) is False:
                        hda.state = hda.states.DISCARDED
                        hda.deleted = True
                        hda.purged = True
                    else:
                        hda.state = hda.states.OK
                    self.sa_session.add(hda)
                    self.sa_session.flush()
                    new_history.add_dataset(hda, genome_build=None)
                    hda.hid = dataset_attrs['hid']  # Overwrite default hid set when HDA added to history.
                    self.sa_session.flush()
                    if dataset_attrs.get('exported', True) is True:
                        # Do security check and move/copy dataset data.
                        temp_dataset_file_name = \
                            os.path.realpath(os.path.abspath(os.path.join(archive_dir, dataset_attrs['file_name'])))
                        if not file_in_dir(temp_dataset_file_name, os.path.join(archive_dir, "datasets")):
                            raise MalformedContents("Invalid dataset path: %s" % temp_dataset_file_name)
                        self.app.object_store.update_from_file(hda.dataset, file_name=temp_dataset_file_name, create=True)

                        # Import additional files if present. Histories exported previously might not have this attribute set.
                        dataset_extra_files_path = dataset_attrs.get('extra_files_path', None)
                        if dataset_extra_files_path:
                            try:
                                file_list = os.listdir(os.path.join(archive_dir, dataset_extra_files_path))
                            except OSError:
                                file_list = []

                            if file_list:
                                for extra_file in file_list:
                                    self.app.object_store.update_from_file(
                                        hda.dataset, extra_dir='dataset_%s_files' % hda.dataset.id,
                                        alt_name=extra_file, file_name=os.path.join(archive_dir, dataset_extra_files_path, extra_file),
                                        create=True)
                        hda.dataset.set_total_size()  # update the filesize record in the database

                    if user:
                        add_item_annotation(self.sa_session, user, hda, dataset_attrs['annotation'])
                        # TODO: Set tags.

                    self.app.datatypes_registry.set_external_metadata_tool.regenerate_imported_metadata_if_needed(
                        hda, new_history, jiha.job
                    )

                #
                # Create jobs.
                #

                # Decode jobs attributes.
                def as_hda(obj_dct):
                    """ Hook to 'decode' an HDA; method uses history and HID to get the HDA represented by
                        the encoded object. This only works because HDAs are created above. """
                    if obj_dct.get('__HistoryDatasetAssociation__', False):
                        return self.sa_session.query(model.HistoryDatasetAssociation) \
                            .filter_by(history=new_history, hid=obj_dct['hid']).first()
                    return obj_dct
                jobs_attr_file_name = os.path.join(archive_dir, ATTRS_FILENAME_JOBS)
                jobs_attrs = load(open(jobs_attr_file_name), object_hook=as_hda)

                # Create each job.
                for job_attrs in jobs_attrs:
                    imported_job = model.Job()
                    imported_job.user = user
                    # TODO: set session?
                    # imported_job.session = trans.get_galaxy_session().id
                    imported_job.history = new_history
                    imported_job.imported = True
                    imported_job.tool_id = job_attrs['tool_id']
                    imported_job.tool_version = job_attrs['tool_version']
                    imported_job.set_state(job_attrs['state'])
                    imported_job.info = job_attrs.get('info', None)
                    imported_job.exit_code = job_attrs.get('exit_code', None)
                    imported_job.traceback = job_attrs.get('traceback', None)
                    imported_job.stdout = job_attrs.get('stdout', None)
                    imported_job.stderr = job_attrs.get('stderr', None)
                    imported_job.command_line = job_attrs.get('command_line', None)
                    try:
                        imported_job.create_time = datetime.datetime.strptime(job_attrs["create_time"], "%Y-%m-%dT%H:%M:%S.%f")
                        imported_job.update_time = datetime.datetime.strptime(job_attrs["update_time"], "%Y-%m-%dT%H:%M:%S.%f")
                    except Exception:
                        pass
                    self.sa_session.add(imported_job)
                    self.sa_session.flush()

                    class HistoryDatasetAssociationIDEncoder(json.JSONEncoder):
                        """ Custom JSONEncoder for a HistoryDatasetAssociation that encodes an HDA as its ID. """

                        def default(self, obj):
                            """ Encode an HDA, default encoding for everything else. """
                            if isinstance(obj, model.HistoryDatasetAssociation):
                                return obj.id
                            return json.JSONEncoder.default(self, obj)

                    for name, value in job_attrs['params'].items():
                        # Transform parameter values when necessary.
                        if isinstance(value, model.HistoryDatasetAssociation):
                            # HDA input: use hid to find input.
                            input_hda = self.sa_session.query(model.HistoryDatasetAssociation) \
                                            .filter_by(history=new_history, hid=value.hid).first()
                            value = input_hda.id
                        imported_job.add_parameter(name, dumps(value, cls=HistoryDatasetAssociationIDEncoder))

                    # Connect jobs to output datasets.
                    for output_hid in job_attrs['output_datasets']:
                        output_hda = self.sa_session.query(model.HistoryDatasetAssociation) \
                            .filter_by(history=new_history, hid=output_hid).first()
                        if output_hda:
                            imported_job.add_output_dataset(output_hda.name, output_hda)

                    # Connect jobs to input datasets.
                    if 'input_mapping' in job_attrs:
                        for input_name, input_hid in job_attrs['input_mapping'].items():
                            input_hda = self.sa_session.query(model.HistoryDatasetAssociation) \
                                            .filter_by(history=new_history, hid=input_hid).first()
                            if input_hda:
                                imported_job.add_input_dataset(input_name, input_hda)

                    self.sa_session.flush()

                # Done importing.
                new_history.importing = False
                self.sa_session.flush()

                # Cleanup.
                if os.path.exists(archive_dir):
                    shutil.rmtree(archive_dir)
            except Exception as e:
                jiha.job.stderr += "Error cleaning up history import job: %s" % e
                self.sa_session.flush()
                raise


class JobExportHistoryArchiveWrapper:
    """
    Class provides support for performing jobs that export a history to an
    archive.
    """

    def __init__(self, job_id):
        self.job_id = job_id

    def get_history_datasets(self, trans, history):
        """
        Returns history's datasets.
        """
        query = (trans.sa_session.query(trans.model.HistoryDatasetAssociation)
                 .filter(trans.model.HistoryDatasetAssociation.history == history)
                 .join("dataset")
                 .options(eagerload_all("dataset.actions"))
                 .order_by(trans.model.HistoryDatasetAssociation.hid)
                 .filter(trans.model.HistoryDatasetAssociation.deleted == expression.false())
                 .filter(trans.model.Dataset.purged == expression.false()))
        return query.all()

    # TODO: should use db_session rather than trans in this method.
    def setup_job(self, trans, jeha, include_hidden=False, include_deleted=False):
        """ Perform setup for job to export a history into an archive. Method generates
            attribute files for export, sets the corresponding attributes in the jeha
            object, and returns a command line for running the job. The command line
            includes the command, inputs, and options; it does not include the output
            file because it must be set at runtime. """

        #
        # Helper methods/classes.
        #

        def prepare_metadata(metadata):
            """ Prepare metatdata for exporting. """
            for name, value in list(metadata.items()):
                # Metadata files are not needed for export because they can be
                # regenerated.
                if isinstance(value, trans.app.model.MetadataFile):
                    del metadata[name]
            return metadata

        class HistoryDatasetAssociationEncoder(json.JSONEncoder):
            """ Custom JSONEncoder for a HistoryDatasetAssociation. """

            def default(self, obj):
                """ Encode an HDA, default encoding for everything else. """
                if isinstance(obj, trans.app.model.HistoryDatasetAssociation):
                    rval = {
                        "__HistoryDatasetAssociation__": True,
                        "create_time": obj.create_time.__str__(),
                        "update_time": obj.update_time.__str__(),
                        "hid": obj.hid,
                        "name": unicodify(obj.name),
                        "info": unicodify(obj.info),
                        "blurb": obj.blurb,
                        "peek": obj.peek,
                        "extension": obj.extension,
                        "metadata": prepare_metadata(dict(obj.metadata.items())),
                        "parent_id": obj.parent_id,
                        "designation": obj.designation,
                        "deleted": obj.deleted,
                        "visible": obj.visible,
                        "uuid": (lambda uuid: str(uuid) if uuid else None)(obj.dataset.uuid),
                        "annotation": unicodify(getattr(obj, 'annotation', '')),
                        "tags": obj.make_tag_string_list()
                    }

                    try:
                        rval['file_name'] = obj.file_name
                    except ObjectNotFound:
                        rval['file_name'] = None

                    if obj.extra_files_path_exists():
                        rval['extra_files_path'] = obj.extra_files_path
                    else:
                        rval['extra_files_path'] = None

                    if not obj.visible and not include_hidden:
                        rval['exported'] = False
                    elif obj.deleted and not include_deleted:
                        rval['exported'] = False
                    else:
                        rval['exported'] = True
                    return rval
                return json.JSONEncoder.default(self, obj)

        #
        # Create attributes/metadata files for export.
        #
        temp_output_dir = tempfile.mkdtemp()

        # Write history attributes to file.
        history = jeha.history
        history_attrs = {
            "create_time": history.create_time.__str__(),
            "update_time": history.update_time.__str__(),
            "name": unicodify(history.name),
            "hid_counter": history.hid_counter,
            "genome_build": history.genome_build,
            "annotation": unicodify(get_item_annotation_str(trans.sa_session, history.user, history)),
            "tags": history.make_tag_string_list()
        }
        history_attrs_filename = os.path.join(temp_output_dir, ATTRS_FILENAME_HISTORY)
        history_attrs_out = open(history_attrs_filename, 'w')
        history_attrs_out.write(dumps(history_attrs))
        history_attrs_out.close()
        jeha.history_attrs_filename = history_attrs_filename

        # Write datasets' attributes to file.
        datasets = self.get_history_datasets(trans, history)
        included_datasets = []
        datasets_attrs = []
        provenance_attrs = []
        for dataset in datasets:
            dataset.annotation = get_item_annotation_str(trans.sa_session, history.user, dataset)
            if (not dataset.visible and not include_hidden) or (dataset.deleted and not include_deleted):
                provenance_attrs.append(dataset)
            else:
                datasets_attrs.append(dataset)
                included_datasets.append(dataset)

        datasets_attrs_filename = os.path.join(temp_output_dir, ATTRS_FILENAME_DATASETS)
        datasets_attrs_out = open(datasets_attrs_filename, 'w')
        datasets_attrs_out.write(dumps(datasets_attrs, cls=HistoryDatasetAssociationEncoder))
        datasets_attrs_out.close()

        provenance_attrs_out = open(datasets_attrs_filename + ".provenance", 'w')
        provenance_attrs_out.write(dumps(provenance_attrs, cls=HistoryDatasetAssociationEncoder))
        provenance_attrs_out.close()

        #
        # Write jobs attributes file.
        #

        # Get all jobs associated with included HDAs.
        jobs_dict = {}
        for hda in included_datasets:
            # Get the associated job, if any. If this hda was copied from another,
            # we need to find the job that created the origial hda
            job_hda = hda
            while job_hda.copied_from_history_dataset_association:  # should this check library datasets as well?
                job_hda = job_hda.copied_from_history_dataset_association
            if not job_hda.creating_job_associations:
                # No viable HDA found.
                continue

            # Get the job object.
            job = None
            for assoc in job_hda.creating_job_associations:
                job = assoc.job
                break
            if not job:
                # No viable job.
                continue

            jobs_dict[job.id] = job

        # Get jobs' attributes.
        jobs_attrs = []
        for id, job in jobs_dict.items():
            job_attrs = {}
            job_attrs['tool_id'] = job.tool_id
            job_attrs['tool_version'] = job.tool_version
            job_attrs['state'] = job.state
            job_attrs['info'] = job.info
            job_attrs['traceback'] = job.traceback
            job_attrs['command_line'] = job.command_line
            job_attrs['stderr'] = job.stderr
            job_attrs['stdout'] = job.stdout
            job_attrs['exit_code'] = job.exit_code
            job_attrs['create_time'] = job.create_time.isoformat()
            job_attrs['update_time'] = job.update_time.isoformat()

            # Get the job's parameters
            try:
                params_objects = job.get_param_values(trans.app)
            except Exception:
                # Could not get job params.
                continue

            params_dict = {}
            for name, value in params_objects.items():
                params_dict[name] = value
            job_attrs['params'] = params_dict

            # -- Get input, output datasets. --

            input_mapping = {}
            for assoc in job.input_datasets:
                # Optional data inputs will not have a dataset.
                if assoc.dataset:
                    input_mapping[assoc.name] = assoc.dataset.hid
            job_attrs['input_mapping'] = input_mapping
            output_datasets = [assoc.dataset.hid for assoc in job.output_datasets]
            job_attrs['output_datasets'] = output_datasets

            jobs_attrs.append(job_attrs)

        jobs_attrs_filename = os.path.join(temp_output_dir, ATTRS_FILENAME_JOBS)
        jobs_attrs_out = open(jobs_attrs_filename, 'w')
        jobs_attrs_out.write(dumps(jobs_attrs, cls=HistoryDatasetAssociationEncoder))
        jobs_attrs_out.close()

        #
        # Create and return command line for running tool.
        #
        options = "--galaxy-version '%s'" % VERSION_MAJOR
        if jeha.compressed:
            options += " -G"
        return "%s %s" % (options, temp_output_dir)

    def cleanup_after_job(self, db_session):
        """ Remove temporary directory and attribute files generated during setup for this job. """
        # Get jeha for job.
        jeha = db_session.query(model.JobExportHistoryArchive).filter_by(job_id=self.job_id).first()
        if jeha:
            temp_dir = jeha.temp_directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                log.debug('Error deleting directory containing attribute files (%s): %s' % (temp_dir, e))
