#!/usr/bin/env python
from __future__ import print_function

import argparse
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from time import strftime

import sqlalchemy as sa
from sqlalchemy import and_, false, null, true
from sqlalchemy.orm import eagerload

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import galaxy.config
from galaxy.datatypes.registry import Registry
from galaxy.exceptions import ObjectNotFound
from galaxy.objectstore import build_object_store_from_config
from galaxy.util import unicodify
from galaxy.util.script import app_properties_from_args, populate_config_args

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))

assert sys.version_info[:2] >= (2, 6)


def main():
    """
    Managing library datasets is a bit complex, so here is a scenario that hopefully provides clarification.  The complexities
    of handling library datasets is mostly contained in the delete_datasets() method in this script.

    Assume we have 1 library dataset with: LibraryDatasetDatasetAssociation -> LibraryDataset and Dataset
    At this point, we have the following database column values:

    LibraryDatasetDatasetAssociation deleted: False
    LibraryDataset deleted: False, purged: False
    Dataset deleted: False purged: False

    1. A user deletes the assumed dataset above from a data library via a UI menu option.
    This action results in the following database column values (changes from previous step marked with *):

    LibraryDatasetDatasetAssociation deleted: False
    LibraryDataset deleted: True*, purged: False
    Dataset deleted: False, purged: False

    2. After the number of days configured for the delete_datasets() method (option -6 below) have passed, execution
    of the delete_datasets() method results in the following database column values (changes from previous step marked with *):

    LibraryDatasetDatasetAssociation deleted: True*
    LibraryDataset deleted: True, purged: True*
    Dataset deleted: True*, purged: False

    3. After the number of days configured for the purge_datasets() method (option -3 below) have passed, execution
    of the purge_datasets() method results in the following database column values (changes from previous step marked with *):

    LibraryDatasetDatasetAssociation deleted: True
    LibraryDataset deleted: True, purged: True
    Dataset deleted: True, purged: True* (dataset file removed from disk if -r flag is used)

    This scenario is about as simple as it gets.  Keep in mind that a Dataset object can have many HistoryDatasetAssociations
    and many LibraryDatasetDatasetAssociations, and a LibraryDataset can have many LibraryDatasetDatasetAssociations.
    Another way of stating it is: LibraryDatasetDatasetAssociation objects map LibraryDataset objects to Dataset objects,
    and Dataset objects may be mapped to History objects via HistoryDatasetAssociation objects.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('legacy_config', metavar='CONFIG', type=str,
                        default=None,
                        nargs='?',
                        help='config file (legacy, use --config instead)')
    parser.add_argument("-d", "--days", dest="days", action="store", type=int, help="number of days (60)", default=60)
    parser.add_argument("-r", "--remove_from_disk", action="store_true", dest="remove_from_disk", help="remove datasets from disk when purged", default=False)
    parser.add_argument("-i", "--info_only", action="store_true", dest="info_only", help="info about the requested action", default=False)
    parser.add_argument("-f", "--force_retry", action="store_true", dest="force_retry", help="performs the requested actions, but ignores whether it might have been done before. Useful when -r wasn't used, but should have been", default=False)
    parser.add_argument("-1", "--delete_userless_histories", action="store_true", dest="delete_userless_histories", default=False, help="delete userless histories and datasets")
    parser.add_argument("-2", "--purge_histories", action="store_true", dest="purge_histories", default=False, help="purge deleted histories")
    parser.add_argument("-3", "--purge_datasets", action="store_true", dest="purge_datasets", default=False, help="purge deleted datasets")
    parser.add_argument("-4", "--purge_libraries", action="store_true", dest="purge_libraries", default=False, help="purge deleted libraries")
    parser.add_argument("-5", "--purge_folders", action="store_true", dest="purge_folders", default=False, help="purge deleted library folders")
    parser.add_argument("-6", "--delete_datasets", action="store_true", dest="delete_datasets", default=False, help="mark deletable datasets as deleted and purge associated dataset instances")
    populate_config_args(parser)

    args = parser.parse_args()
    config_override = None
    if args.legacy_config:
        config_override = args.legacy_config

    if not (args.purge_folders ^ args.delete_userless_histories ^
            args.purge_libraries ^ args.purge_histories ^
            args.purge_datasets ^ args.delete_datasets):
        parser.print_help()
        sys.exit(0)

    if args.remove_from_disk and args.info_only:
        parser.error("remove_from_disk and info_only are mutually exclusive")

    app_properties = app_properties_from_args(args, legacy_config_override=config_override)
    config = galaxy.config.Configuration(**app_properties)
    app = CleanupDatasetsApplication(config)
    cutoff_time = datetime.utcnow() - timedelta(days=args.days)
    now = strftime("%Y-%m-%d %H:%M:%S")

    print("##########################################")
    print("\n# %s - Handling stuff older than %i days" % (now, args.days))

    if args.info_only:
        print("# Displaying info only ( --info_only )\n")
    elif args.remove_from_disk:
        print("Datasets will be removed from disk.\n")
    else:
        print("Datasets will NOT be removed from disk.\n")

    if args.delete_userless_histories:
        delete_userless_histories(app, cutoff_time, info_only=args.info_only, force_retry=args.force_retry)
    elif args.purge_histories:
        purge_histories(app, cutoff_time, args.remove_from_disk, info_only=args.info_only, force_retry=args.force_retry)
    elif args.purge_datasets:
        purge_datasets(app, cutoff_time, args.remove_from_disk, info_only=args.info_only, force_retry=args.force_retry)
    elif args.purge_libraries:
        purge_libraries(app, cutoff_time, args.remove_from_disk, info_only=args.info_only, force_retry=args.force_retry)
    elif args.purge_folders:
        purge_folders(app, cutoff_time, args.remove_from_disk, info_only=args.info_only, force_retry=args.force_retry)
    elif args.delete_datasets:
        delete_datasets(app, cutoff_time, args.remove_from_disk, info_only=args.info_only, force_retry=args.force_retry)

    app.shutdown()
    sys.exit(0)


def delete_userless_histories(app, cutoff_time, info_only=False, force_retry=False):
    # Deletes userless histories whose update_time value is older than the cutoff_time.
    # The purge history script will handle marking DatasetInstances as deleted.
    # Nothing is removed from disk yet.
    history_count = 0
    start = time.time()
    if force_retry:
        histories = app.sa_session.query(app.model.History) \
                                  .filter(and_(app.model.History.table.c.user_id == null(),
                                               app.model.History.table.c.update_time < cutoff_time))
    else:
        histories = app.sa_session.query(app.model.History) \
                                  .filter(and_(app.model.History.table.c.user_id == null(),
                                               app.model.History.table.c.deleted == false(),
                                               app.model.History.table.c.update_time < cutoff_time))
    for history in histories:
        if not info_only:
            print("Deleting history id ", history.id)
            history.deleted = True
            app.sa_session.add(history)
            app.sa_session.flush()
        history_count += 1
    stop = time.time()
    print("Deleted %d histories" % history_count)
    print("Elapsed time: ", stop - start)
    print("##########################################")


def purge_histories(app, cutoff_time, remove_from_disk, info_only=False, force_retry=False):
    # Purges deleted histories whose update_time is older than the cutoff_time.
    # The dataset associations of each history are also marked as deleted.
    # The Purge Dataset method will purge each Dataset as necessary
    # history.purged == True simply means that it can no longer be undeleted
    # i.e. all associated datasets are marked as deleted
    history_count = 0
    start = time.time()
    if force_retry:
        histories = app.sa_session.query(app.model.History) \
                                  .filter(and_(app.model.History.table.c.deleted == true(),
                                               app.model.History.table.c.update_time < cutoff_time)) \
                                  .options(eagerload('datasets'))
    else:
        histories = app.sa_session.query(app.model.History) \
                                  .filter(and_(app.model.History.table.c.deleted == true(),
                                               app.model.History.table.c.purged == false(),
                                               app.model.History.table.c.update_time < cutoff_time)) \
                                  .options(eagerload('datasets'))
    for history in histories:
        print("### Processing history id %d (%s)" % (history.id, unicodify(history.name)))
        for dataset_assoc in history.datasets:
            _purge_dataset_instance(dataset_assoc, app, remove_from_disk, info_only=info_only)  # mark a DatasetInstance as deleted, clear associated files, and mark the Dataset as deleted if it is deletable
        if not info_only:
            # TODO: should the Delete DefaultHistoryPermissions be deleted here?  This was incorrectly
            # done in the _list_delete() method of the history controller, so copied it here.  Not sure
            # if we should ever delete info like this from the db though, so commented out for now...
            # for dhp in history.default_permissions:
            #     dhp.delete()
            print("Purging history id ", history.id)
            history.purged = True
            app.sa_session.add(history)
            app.sa_session.flush()
        else:
            print("History id %d will be purged (without 'info_only' mode)" % history.id)
        history_count += 1
    stop = time.time()
    print('Purged %d histories.' % history_count)
    print("Elapsed time: ", stop - start)
    print("##########################################")


def purge_libraries(app, cutoff_time, remove_from_disk, info_only=False, force_retry=False):
    # Purges deleted libraries whose update_time is older than the cutoff_time.
    # The dataset associations of each library are also marked as deleted.
    # The Purge Dataset method will purge each Dataset as necessary
    # library.purged == True simply means that it can no longer be undeleted
    # i.e. all associated LibraryDatasets/folders are marked as deleted
    library_count = 0
    start = time.time()
    if force_retry:
        libraries = app.sa_session.query(app.model.Library) \
                                  .filter(and_(app.model.Library.table.c.deleted == true(),
                                               app.model.Library.table.c.update_time < cutoff_time))
    else:
        libraries = app.sa_session.query(app.model.Library) \
                                  .filter(and_(app.model.Library.table.c.deleted == true(),
                                               app.model.Library.table.c.purged == false(),
                                               app.model.Library.table.c.update_time < cutoff_time))
    for library in libraries:
        _purge_folder(library.root_folder, app, remove_from_disk, info_only=info_only)
        if not info_only:
            print("Purging library id ", library.id)
            library.purged = True
            app.sa_session.add(library)
            app.sa_session.flush()
        library_count += 1
    stop = time.time()
    print('# Purged %d libraries .' % library_count)
    print("Elapsed time: ", stop - start)
    print("##########################################")


def purge_folders(app, cutoff_time, remove_from_disk, info_only=False, force_retry=False):
    # Purges deleted folders whose update_time is older than the cutoff_time.
    # The dataset associations of each folder are also marked as deleted.
    # The Purge Dataset method will purge each Dataset as necessary
    # libraryFolder.purged == True simply means that it can no longer be undeleted
    # i.e. all associated LibraryDatasets/folders are marked as deleted
    folder_count = 0
    start = time.time()
    if force_retry:
        folders = app.sa_session.query(app.model.LibraryFolder) \
                                .filter(and_(app.model.LibraryFolder.table.c.deleted == true(),
                                             app.model.LibraryFolder.table.c.update_time < cutoff_time))
    else:
        folders = app.sa_session.query(app.model.LibraryFolder) \
                                .filter(and_(app.model.LibraryFolder.table.c.deleted == true(),
                                             app.model.LibraryFolder.table.c.purged == false(),
                                             app.model.LibraryFolder.table.c.update_time < cutoff_time))
    for folder in folders:
        _purge_folder(folder, app, remove_from_disk, info_only=info_only)
        folder_count += 1
    stop = time.time()
    print('# Purged %d folders.' % folder_count)
    print("Elapsed time: ", stop - start)
    print("##########################################")


def delete_datasets(app, cutoff_time, remove_from_disk, info_only=False, force_retry=False):
    # Marks datasets as deleted if associated items are all deleted.
    start = time.time()
    if force_retry:
        history_dataset_ids_query = sa.select((app.model.Dataset.table.c.id,
                                               app.model.Dataset.table.c.state),
                                              whereclause=app.model.HistoryDatasetAssociation.table.c.update_time < cutoff_time,
                                              from_obj=[sa.outerjoin(app.model.Dataset.table,
                                                                     app.model.HistoryDatasetAssociation.table)])
        library_dataset_ids_query = sa.select((app.model.LibraryDataset.table.c.id,
                                               app.model.LibraryDataset.table.c.deleted),
                                              whereclause=app.model.LibraryDataset.table.c.update_time < cutoff_time,
                                              from_obj=[app.model.LibraryDataset.table])
    else:
        # We really only need the id column here, but sqlalchemy barfs when trying to select only 1 column
        history_dataset_ids_query = sa.select((app.model.Dataset.table.c.id,
                                               app.model.Dataset.table.c.state),
                                              whereclause=and_(app.model.Dataset.table.c.deleted == false(),
                                                               app.model.HistoryDatasetAssociation.table.c.update_time < cutoff_time,
                                                               app.model.HistoryDatasetAssociation.table.c.deleted == true()),
                                              from_obj=[sa.outerjoin(app.model.Dataset.table,
                                                                     app.model.HistoryDatasetAssociation.table)])
        library_dataset_ids_query = sa.select((app.model.LibraryDataset.table.c.id,
                                               app.model.LibraryDataset.table.c.deleted),
                                              whereclause=and_(app.model.LibraryDataset.table.c.deleted == true(),
                                                               app.model.LibraryDataset.table.c.purged == false(),
                                                               app.model.LibraryDataset.table.c.update_time < cutoff_time),
                                              from_obj=[app.model.LibraryDataset.table])
    deleted_dataset_count = 0
    deleted_instance_count = 0
    skip = []
    # Handle library datasets.  This is a bit tricky, so here's some clarification.  We have a list of all
    # LibraryDatasets that were marked deleted before our cutoff_time, but have not yet been marked purged.
    # A LibraryDataset object is marked purged when all of its LibraryDatasetDatasetAssociations have been
    # marked deleted.  When a LibraryDataset has been marked purged, it can never be undeleted in the data
    # library.  We have several steps to complete here.  For each LibraryDataset, get its associated Dataset
    # and add it to our accrued list of Datasets for later processing.  We mark  as deleted all of its
    # LibraryDatasetDatasetAssociations.  Then we mark the LibraryDataset as purged.  We then process our
    # list of Datasets.
    library_dataset_ids = [row.id for row in library_dataset_ids_query.execute()]
    dataset_ids = []
    for library_dataset_id in library_dataset_ids:
        print("######### Processing LibraryDataset id:", library_dataset_id)
        # Get the LibraryDataset and the current LibraryDatasetDatasetAssociation objects
        ld = app.sa_session.query(app.model.LibraryDataset).get(library_dataset_id)
        ldda = ld.library_dataset_dataset_association
        # Append the associated Dataset object's id to our list of dataset_ids
        dataset_ids.append(ldda.dataset_id)
        # Mark all of the LibraryDataset's associated LibraryDatasetDatasetAssociation objects' as deleted
        if not ldda.deleted:
            ldda.deleted = True
            app.sa_session.add(ldda)
            print("Marked associated LibraryDatasetDatasetAssociation id %d as deleted" % ldda.id)
        for expired_ldda in ld.expired_datasets:
            if not expired_ldda.deleted:
                expired_ldda.deleted = True
                app.sa_session.add(expired_ldda)
                print("Marked associated expired LibraryDatasetDatasetAssociation id %d as deleted" % ldda.id)
        # Mark the LibraryDataset as purged
        ld.purged = True
        app.sa_session.add(ld)
        print("Marked LibraryDataset id %d as purged" % ld.id)
        app.sa_session.flush()
    # Add all datasets associated with Histories to our list
    dataset_ids.extend([row.id for row in history_dataset_ids_query.execute()])
    # Process each of the Dataset objects
    for dataset_id in dataset_ids:
        dataset = app.sa_session.query(app.model.Dataset).get(dataset_id)
        if dataset.id in skip:
            continue
        skip.append(dataset.id)
        print("######### Processing dataset id:", dataset_id)
        if not _dataset_is_deletable(dataset):
            print("Dataset is not deletable (shared between multiple histories/libraries, at least one is not deleted)")
            continue
        deleted_dataset_count += 1
        for dataset_instance in dataset.history_associations + dataset.library_associations:
            # Mark each associated HDA as deleted
            _purge_dataset_instance(dataset_instance, app, remove_from_disk, info_only=info_only, is_deletable=True)
            deleted_instance_count += 1
    stop = time.time()
    print("Examined %d datasets, marked %d datasets and %d dataset instances (HDA) as deleted" % (len(skip), deleted_dataset_count, deleted_instance_count))
    print("Total elapsed time: ", stop - start)
    print("##########################################")


def purge_datasets(app, cutoff_time, remove_from_disk, info_only=False, force_retry=False):
    # Purges deleted datasets whose update_time is older than cutoff_time.  Files may or may
    # not be removed from disk.
    dataset_count = 0
    disk_space = 0
    start = time.time()
    if force_retry:
        datasets = app.sa_session.query(app.model.Dataset) \
                                 .filter(and_(app.model.Dataset.table.c.deleted == true(),
                                              app.model.Dataset.table.c.purgable == true(),
                                              app.model.Dataset.table.c.update_time < cutoff_time))
    else:
        datasets = app.sa_session.query(app.model.Dataset) \
                                 .filter(and_(app.model.Dataset.table.c.deleted == true(),
                                              app.model.Dataset.table.c.purgable == true(),
                                              app.model.Dataset.table.c.purged == false(),
                                              app.model.Dataset.table.c.update_time < cutoff_time))
    for dataset in datasets:
        file_size = dataset.file_size
        _purge_dataset(app, dataset, remove_from_disk, info_only=info_only)
        dataset_count += 1
        try:
            disk_space += file_size
        except Exception:
            pass
    stop = time.time()
    print('Purged %d datasets' % dataset_count)
    if remove_from_disk:
        print('Freed disk space: ', disk_space)
    print("Elapsed time: ", stop - start)
    print("##########################################")


def _purge_dataset_instance(dataset_instance, app, remove_from_disk, info_only=False, is_deletable=False):
    # A dataset_instance is either a HDA or an LDDA.  Purging a dataset instance marks the instance as deleted,
    # and marks the associated dataset as deleted if it is not associated with another active DatsetInstance.
    if not info_only:
        print("Marking as deleted: %s id %d (for dataset id %d)" %
              (dataset_instance.__class__.__name__, dataset_instance.id, dataset_instance.dataset.id))
        dataset_instance.mark_deleted()
        dataset_instance.clear_associated_files()
        app.sa_session.add(dataset_instance)
        app.sa_session.flush()
        app.sa_session.refresh(dataset_instance.dataset)
    else:
        print("%s id %d (for dataset id %d) will be marked as deleted (without 'info_only' mode)" %
              (dataset_instance.__class__.__name__, dataset_instance.id, dataset_instance.dataset.id))
    if is_deletable or _dataset_is_deletable(dataset_instance.dataset):
        # Calling methods may have already checked _dataset_is_deletable, if so, is_deletable should be True
        _delete_dataset(dataset_instance.dataset, app, remove_from_disk, info_only=info_only, is_deletable=is_deletable)
    else:
        if info_only:
            print("Not deleting dataset ", dataset_instance.dataset.id, " (will be possibly deleted without 'info_only' mode)")
        else:
            print("Not deleting dataset %d (shared between multiple histories/libraries, at least one not deleted)" % dataset_instance.dataset.id)


def _dataset_is_deletable(dataset):
    # a dataset is deletable when it no longer has any non-deleted associations
    return not bool(dataset.active_history_associations or dataset.active_library_associations)


def _delete_dataset(dataset, app, remove_from_disk, info_only=False, is_deletable=False):
    # Marks a base dataset as deleted, hdas/lddas associated with dataset can no longer be undeleted.
    # Metadata files attached to associated dataset Instances is removed now.
    if not is_deletable and not _dataset_is_deletable(dataset):
        print("This Dataset (%i) is not deletable, associated Metadata Files will not be removed.\n" % (dataset.id))
    else:
        # Mark all associated MetadataFiles as deleted and purged and remove them from disk
        metadata_files = []
        # lets create a list of metadata files, then perform actions on them
        for hda in dataset.history_associations:
            for metadata_file in app.sa_session.query(app.model.MetadataFile) \
                                               .filter(app.model.MetadataFile.table.c.hda_id == hda.id):
                metadata_files.append(metadata_file)
        for ldda in dataset.library_associations:
            for metadata_file in app.sa_session.query(app.model.MetadataFile) \
                                               .filter(app.model.MetadataFile.table.c.lda_id == ldda.id):
                metadata_files.append(metadata_file)
        for metadata_file in metadata_files:
            op_description = "marked as deleted"
            if remove_from_disk:
                op_description = op_description + " and purged from disk"
            if info_only:
                print("The following metadata files attached to associations of Dataset '%s' will be %s (without 'info_only' mode):" % (dataset.id, op_description))
            else:
                print("The following metadata files attached to associations of Dataset '%s' have been %s:" % (dataset.id, op_description))
                if remove_from_disk:
                    try:
                        print("Removing disk file ", metadata_file.file_name)
                        os.unlink(metadata_file.file_name)
                    except Exception as e:
                        print("Error, exception: %s caught attempting to purge metadata file %s\n" % (str(e), metadata_file.file_name))
                    metadata_file.purged = True
                    app.sa_session.add(metadata_file)
                    app.sa_session.flush()
                metadata_file.deleted = True
                app.sa_session.add(metadata_file)
                app.sa_session.flush()
            print("%s" % metadata_file.file_name)
        if not info_only:
            print("Deleting dataset id", dataset.id)
            dataset.deleted = True
            app.sa_session.add(dataset)
            app.sa_session.flush()
        else:
            print("Dataset %i will be deleted (without 'info_only' mode)" % (dataset.id))


def _purge_dataset(app, dataset, remove_from_disk, info_only=False):
    if dataset.deleted:
        try:
            if dataset.purgable and _dataset_is_deletable(dataset):
                if not info_only:
                    # Remove files from disk and update the database
                    if remove_from_disk:
                        # TODO: should permissions on the dataset be deleted here?
                        print("Removing disk, file ", dataset.file_name)
                        os.unlink(dataset.file_name)
                        # Remove associated extra files from disk if they exist
                        if dataset.extra_files_path and os.path.exists(dataset.extra_files_path):
                            shutil.rmtree(dataset.extra_files_path)  # we need to delete the directory and its contents; os.unlink would always fail on a directory
                        usage_users = []
                        for hda in dataset.history_associations:
                            if not hda.purged:
                                hda.purged = True
                                if hda.history.user is not None and hda.history.user not in usage_users:
                                    usage_users.append(hda.history.user)
                        for user in usage_users:
                            user.adjust_total_disk_usage(-dataset.get_total_size())
                            app.sa_session.add(user)
                    print("Purging dataset id", dataset.id)
                    dataset.purged = True
                    app.sa_session.add(dataset)
                    app.sa_session.flush()
                else:
                    print("Dataset %i will be purged (without 'info_only' mode)" % (dataset.id))
            else:
                print("This dataset (%i) is not purgable, the file (%s) will not be removed.\n" % (dataset.id, dataset.file_name))
        except OSError as exc:
            print("Error, dataset file has already been removed: %s" % str(exc))
            print("Purging dataset id", dataset.id)
            dataset.purged = True
            app.sa_session.add(dataset)
            app.sa_session.flush()
        except ObjectNotFound:
            print("Dataset %i cannot be found in the object store" % dataset.id)
        except Exception as exc:
            print("Error attempting to purge data file: ", dataset.file_name, " error: ", str(exc))
    else:
        print("Error: '%s' has not previously been deleted, so it cannot be purged\n" % dataset.file_name)


def _purge_folder(folder, app, remove_from_disk, info_only=False):
    """Purges a folder and its contents, recursively"""
    for ld in folder.datasets:
        print("Deleting library dataset id ", ld.id)
        ld.deleted = True
        for ldda in [ld.library_dataset_dataset_association] + ld.expired_datasets:
            _purge_dataset_instance(ldda, app, remove_from_disk, info_only=info_only)  # mark a DatasetInstance as deleted, clear associated files, and mark the Dataset as deleted if it is deletable
    for sub_folder in folder.folders:
        _purge_folder(sub_folder, app, remove_from_disk, info_only=info_only)
    if not info_only:
        # TODO: should the folder permissions be deleted here?
        print("Purging folder id ", folder.id)
        folder.purged = True
        app.sa_session.add(folder)
        app.sa_session.flush()


class CleanupDatasetsApplication(object):
    """Encapsulates the state of a Universe application"""
    def __init__(self, config):
        self.object_store = build_object_store_from_config(config)
        # Setup the database engine and ORM
        self.model = galaxy.config.init_models_from_config(config, object_store=self.object_store)
        registry = Registry()
        registry.load_datatypes()
        galaxy.model.set_datatypes_registry(registry)

    @property
    def sa_session(self):
        """
        Returns a SQLAlchemy session -- currently just gets the current
        session from the threadlocal session context, but this is provided
        to allow migration toward a more SQLAlchemy 0.4 style of use.
        """
        return self.model.context.current

    def shutdown(self):
        self.object_store.shutdown()


if __name__ == "__main__":
    main()
