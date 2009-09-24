#!/usr/bin/env python

import os, sys

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources  
pkg_resources.require( "SQLAlchemy >= 0.4" )

import time, ConfigParser, shutil
from datetime import datetime, timedelta
from time import strftime
from optparse import OptionParser

import galaxy.model.mapping
from galaxy.model.orm import and_, eagerload

assert sys.version_info[:2] >= ( 2, 4 )

def main():
    parser = OptionParser()
    parser.add_option( "-d", "--days", dest="days", action="store", type="int", help="number of days (60)", default=60 )
    parser.add_option( "-r", "--remove_from_disk", action="store_true", dest="remove_from_disk", help="remove datasets from disk when purged", default=False )
    parser.add_option( "-i", "--info_only", action="store_true", dest="info_only", help="info about the requested action", default=False )
    parser.add_option( "-f", "--force_retry", action="store_true", dest="force_retry", help="performs the requested actions, but ignores whether it might have been done before. Useful when -r wasn't used, but should have been", default=False )
    
    parser.add_option( "-1", "--delete_userless_histories", action="store_true", dest="delete_userless_histories", default=False, help="delete userless histories and datasets" )
    
    parser.add_option( "-2", "--purge_histories", action="store_true", dest="purge_histories", default=False, help="purge deleted histories" )
    
    parser.add_option( "-3", "--purge_datasets", action="store_true", dest="purge_datasets", default=False, help="purge deleted datasets" )
    
    parser.add_option( "-4", "--purge_libraries", action="store_true", dest="purge_libraries", default=False, help="purge deleted libraries" )
    
    parser.add_option( "-5", "--purge_folders", action="store_true", dest="purge_folders", default=False, help="purge deleted library folders" )
    
    parser.add_option( "-6", "--delete_datasets", action="store_true", dest="delete_datasets", default=False, help="mark deletable datasets as deleted and purge associated dataset instances" )
    
    
    ( options, args ) = parser.parse_args()
    ini_file = args[0]
    
    if not ( options.purge_folders ^ options.delete_userless_histories ^ \
             options.purge_libraries ^ options.purge_histories ^ \
             options.purge_datasets ^ options.delete_datasets ):
        parser.print_help()
        sys.exit(0)
    
    if options.remove_from_disk and options.info_only:
        parser.error( "remove_from_disk and info_only are mutually exclusive" )
    
    conf_parser = ConfigParser.ConfigParser( {'here':os.getcwd()} )
    conf_parser.read( ini_file )
    configuration = {}
    for key, value in conf_parser.items( "app:main" ):
        configuration[key] = value
    
    if 'database_connection' in configuration:
        database_connection = configuration['database_connection']
    else:
        database_connection = "sqlite:///%s?isolation_level=IMMEDIATE" % configuration["database_file"]
    file_path = configuration['file_path']
    app = CleanupDatasetsApplication( database_connection=database_connection, file_path=file_path )
    cutoff_time = datetime.utcnow() - timedelta( days=options.days )
    now = strftime( "%Y-%m-%d %H:%M:%S" )
    
    print "\n# %s - Handling stuff older than %i days\n" % ( now, options.days )
    
    if options.info_only:
        print "# Displaying info only ( --info_only )\n"
    elif options.remove_from_disk:
        print "# Datasets will be removed from disk.\n"
    else:
        print "# Datasets will NOT be removed from disk.\n"
    
    if options.delete_userless_histories:
        delete_userless_histories( app, cutoff_time, info_only = options.info_only, force_retry = options.force_retry )
    elif options.purge_histories:
        purge_histories( app, cutoff_time, options.remove_from_disk, info_only = options.info_only, force_retry = options.force_retry )
    elif options.purge_datasets:
        purge_datasets( app, cutoff_time, options.remove_from_disk, info_only = options.info_only, force_retry = options.force_retry )
    elif options.purge_libraries:
        purge_libraries( app, cutoff_time, options.remove_from_disk, info_only = options.info_only, force_retry = options.force_retry )
    elif options.purge_folders:
        purge_folders( app, cutoff_time, options.remove_from_disk, info_only = options.info_only, force_retry = options.force_retry )
    elif options.delete_datasets:
        delete_datasets( app, cutoff_time, options.remove_from_disk, info_only = options.info_only, force_retry = options.force_retry )
    
    sys.exit(0)

def delete_userless_histories( app, cutoff_time, info_only = False, force_retry = False ):
    # Deletes userless histories whose update_time value is older than the cutoff_time.
    # The purge history script will handle marking DatasetInstances as deleted. 
    # Nothing is removed from disk yet.
    history_count = 0
    print '# The following datasets and associated userless histories have been deleted'
    start = time.clock()
    if force_retry:
        histories = app.model.History.filter( and_( app.model.History.table.c.user_id==None,
                                    app.model.History.table.c.update_time < cutoff_time ) ).all()
    else:
        histories = app.model.History.filter( and_( app.model.History.table.c.user_id==None,
                                    app.model.History.table.c.deleted==False,
                                    app.model.History.table.c.update_time < cutoff_time ) ).all()
    for history in histories:
        if not info_only:
            history.deleted = True
        print "%d" % history.id
        history_count += 1
    app.model.flush()
    stop = time.clock()
    print "# Deleted %d histories.\n" % ( history_count )
    print "Elapsed time: ", stop - start, "\n"
    

def purge_histories( app, cutoff_time, remove_from_disk, info_only = False, force_retry = False ):
    # Purges deleted histories whose update_time is older than the cutoff_time.
    # The dataset associations of each history are also marked as deleted.
    # The Purge Dataset method will purge each Dataset as necessary
    # history.purged == True simply means that it can no longer be undeleted
    # i.e. all associated datasets are marked as deleted
    history_count = 0
    print '# The following datasets and associated deleted histories have been purged'
    start = time.clock()
    if force_retry:
        histories = app.model.History.filter( and_( app.model.History.table.c.deleted==True,
                                    app.model.History.table.c.update_time < cutoff_time ) ) \
                     .options( eagerload( 'datasets' ) ).all()
    else:
        histories = app.model.History.filter( and_( app.model.History.table.c.deleted==True,
                                    app.model.History.table.c.purged==False,
                                    app.model.History.table.c.update_time < cutoff_time ) ) \
                     .options( eagerload( 'datasets' ) ).all()
    for history in histories:
        for dataset_assoc in history.datasets:
            _purge_dataset_instance( dataset_assoc, app, remove_from_disk, info_only = info_only ) #mark a DatasetInstance as deleted, clear associated files, and mark the Dataset as deleted if it is deletable
        if not info_only:
            # TODO: should the Delete DefaultHistoryPermissions be deleted here?  This was incorrectly
            # done in the _list_delete() method of the history controller, so copied it here.  Not sure 
            # if we should ever delete info like this from the db though, so commented out for now...
            #for dhp in history.default_permissions:
            #    dhp.delete()
            history.purged = True
        print "%d" % history.id
        history_count += 1
    app.model.flush()
    stop = time.clock()
    print '# Purged %d histories.' % ( history_count ), '\n'
    print "Elapsed time: ", stop - start, "\n"

def purge_libraries( app, cutoff_time, remove_from_disk, info_only = False, force_retry = False ):
    # Purges deleted libraries whose update_time is older than the cutoff_time.
    # The dataset associations of each library are also marked as deleted.
    # The Purge Dataset method will purge each Dataset as necessary
    # library.purged == True simply means that it can no longer be undeleted
    # i.e. all associated LibraryDatasets/folders are marked as deleted
    library_count = 0
    print '# The following libraries and associated folders have been purged'
    start = time.clock()
    if force_retry:
        libraries = app.model.Library.filter( and_( app.model.Library.table.c.deleted==True,
                                    app.model.Library.table.c.update_time < cutoff_time ) ).all()
    else:
        libraries = app.model.Library.filter( and_( app.model.Library.table.c.deleted==True,
                                    app.model.Library.table.c.purged==False,
                                    app.model.Library.table.c.update_time < cutoff_time ) ).all()
    for library in libraries:
        _purge_folder( library.root_folder, app, remove_from_disk, info_only = info_only )
        if not info_only:
            library.purged = True
        print "%d" % library.id
        library_count += 1
    app.model.flush()
    stop = time.clock()
    print '# Purged %d libraries .' % ( library_count ), '\n'
    print "Elapsed time: ", stop - start, "\n"

def purge_folders( app, cutoff_time, remove_from_disk, info_only = False, force_retry = False ):
    # Purges deleted folders whose update_time is older than the cutoff_time.
    # The dataset associations of each folder are also marked as deleted.
    # The Purge Dataset method will purge each Dataset as necessary
    # libraryFolder.purged == True simply means that it can no longer be undeleted
    # i.e. all associated LibraryDatasets/folders are marked as deleted
    folder_count = 0
    print '# The following folders have been purged'
    start = time.clock()
    if force_retry:
        folders = app.model.LibraryFolder.filter( and_( app.model.LibraryFolder.table.c.deleted==True,
                                    app.model.LibraryFolder.table.c.update_time < cutoff_time ) ).all()
    else:
        folders = app.model.LibraryFolder.filter( and_( app.model.LibraryFolder.table.c.deleted==True,
                                    app.model.LibraryFolder.table.c.purged==False,
                                    app.model.LibraryFolder.table.c.update_time < cutoff_time ) ).all()
    for folder in folders:
        _purge_folder( folder, app, remove_from_disk, info_only = info_only )
        print "%d" % folder.id
        folder_count += 1
    stop = time.clock()
    print '# Purged %d folders.' % ( folder_count ), '\n'
    print "Elapsed time: ", stop - start, "\n"

def delete_datasets( app, cutoff_time, remove_from_disk, info_only = False, force_retry = False ):
    import sqlalchemy as sa
    # Marks datasets as deleted if associated items are all deleted.
    print "######### Starting delete_datasets #########\n"
    start = time.clock()
    if force_retry:
        history_datasets = app.model.Dataset.options( eagerload( "history_associations" ) ) \
                                            .filter( app.model.HistoryDatasetAssociation.table.c.update_time < cutoff_time ).all()
        library_datasets = app.model.Dataset.options( eagerload( "library_associations" ) ) \
                                            .filter( app.model.LibraryDatasetDatasetAssociation.table.c.update_time < cutoff_time ).all()
    else:                                  
        # We really only need the id column here, but sqlalchemy barfs when trying to select only 1 column
        history_dataset_ids_query = sa.select( ( app.model.Dataset.table.c.id,
                                                 app.model.Dataset.table.c.state ),
                                               whereclause = sa.and_( app.model.Dataset.table.c.deleted == False,
                                                                      app.model.HistoryDatasetAssociation.table.c.update_time < cutoff_time,
                                                                      app.model.HistoryDatasetAssociation.table.c.deleted == True ),
                                               from_obj = [ sa.outerjoin( app.model.Dataset.table,
                                                                          app.model.HistoryDatasetAssociation.table ) ] )
        history_dataset_ids = [ row.id for row in history_dataset_ids_query.execute() ]
        print "Time to retrieve ", len( history_dataset_ids ), " history dataset ids: ", time.clock() - start
        library_dataset_ids_query = sa.select( ( app.model.Dataset.table.c.id,
                                                 app.model.Dataset.table.c.state ),
                                                whereclause = sa.and_( app.model.Dataset.table.c.deleted == False,
                                                                       app.model.LibraryDatasetDatasetAssociation.table.c.update_time < cutoff_time,
                                                                       app.model.LibraryDatasetDatasetAssociation.table.c.deleted == True ),
                                                from_obj = [ sa.outerjoin( app.model.Dataset.table,
                                                                           app.model.LibraryDatasetDatasetAssociation.table ) ] )                       
        library_dataset_ids = [ row.id for row in library_dataset_ids_query.execute() ]
        print "Time to retrieve ", len( library_dataset_ids ), " library dataset ids: ", time.clock() - start
    dataset_ids = history_dataset_ids + library_dataset_ids
    skip = []
    deleted_dataset_count = 0
    deleted_instance_count = 0
    for dataset_id in dataset_ids:
        print "Processing dataset id:", dataset_id, "\n"
        dataset = app.model.Dataset.get( id )
        if dataset.id not in skip and _dataset_is_deletable( dataset ):
            deleted_dataset_count += 1
            for dataset_instance in dataset.history_associations + dataset.library_associations:
                print "Associated Dataset instance: ", dataset_instance.__class__.__name__, dataset_instance.id, "\n"
                _purge_dataset_instance( dataset_instance, app, remove_from_disk, include_children=True, info_only=info_only, is_deletable=True )
                deleted_instance_count += 1
        skip.append( dataset.id )
        print "Time to process dataset id: ", dataset.id, " - ", time.clock() - start, "\n\n"
    print "Time to mark datasets deleted: ", time.clock() - start, "\n\n"
    print "Examined %d datasets, marked %d as deleted and purged %d dataset instances\n" % ( len( skip ), deleted_dataset_count, deleted_instance_count )
    print "Total elapsed time: ", time.clock() - start, "\n"
    print "######### Finished delete_datasets #########\n"

def purge_datasets( app, cutoff_time, remove_from_disk, info_only = False, force_retry = False ):
    # Purges deleted datasets whose update_time is older than cutoff_time.  Files may or may
    # not be removed from disk.
    dataset_count = 0
    disk_space = 0
    print '# The following deleted datasets have been purged'
    start = time.clock()
    if force_retry:
        datasets = app.model.Dataset.filter( and_( app.model.Dataset.table.c.deleted==True,
                                   app.model.Dataset.table.c.purgable==True,
                                   app.model.Dataset.table.c.update_time < cutoff_time ) ).all()
    else:
        datasets = app.model.Dataset.filter( and_( app.model.Dataset.table.c.deleted==True,
                                   app.model.Dataset.table.c.purgable==True,
                                   app.model.Dataset.table.c.purged==False,
                                   app.model.Dataset.table.c.update_time < cutoff_time ) ).all()
    for dataset in datasets:
        file_size = dataset.file_size
        _purge_dataset( dataset, remove_from_disk, info_only = info_only )
        dataset_count += 1
        try:
            disk_space += file_size
        except:
            pass
    stop = time.clock()
    print '# %d datasets purged\n' % dataset_count
    if remove_from_disk:
        print '# Freed disk space: ', disk_space, '\n'
    print "Elapsed time: ", stop - start, "\n"


def _purge_dataset_instance( dataset_instance, app, remove_from_disk, include_children=True, info_only=False, is_deletable=False ):
    # A dataset_instance is either a HDA or an LDDA.  Purging a dataset instance marks the instance as deleted, 
    # and marks the associated dataset as deleted if it is not associated with another active DatsetInstance.
    if not info_only:
        dataset_instance.mark_deleted( include_children = include_children )
        dataset_instance.clear_associated_files()
        dataset_instance.flush()
        dataset_instance.dataset.refresh()
    if is_deletable or _dataset_is_deletable( dataset_instance.dataset ):
        # Calling methods may have already checked _dataset_is_deletable, if so, is_deletable should be True
        _delete_dataset( dataset_instance.dataset, app, remove_from_disk, info_only = info_only )
    #need to purge children here
    if include_children:
        for child in dataset_instance.children:
            _purge_dataset_instance( child, app, remove_from_disk, include_children = include_children, info_only = info_only )

def _dataset_is_deletable( dataset ):
    #a dataset is deletable when it no longer has any non-deleted associations
    return not bool( dataset.active_history_associations or dataset.active_library_associations )

def _delete_dataset( dataset, app, remove_from_disk, info_only = False ):
    #marks a base dataset as deleted, hdas/ldas associated with dataset can no longer be undeleted
    #metadata files attached to associated dataset Instances is removed now
    if not _dataset_is_deletable( dataset ):
        print "# This Dataset (%i) is not deletable, associated Metadata Files will not be removed.\n" % ( dataset.id )
    else:
        # Mark all associated MetadataFiles as deleted and purged and remove them from disk
        metadata_files = []
        #lets create a list of metadata files, then perform actions on them
        for hda in dataset.history_associations:
            for metadata_file in app.model.MetadataFile.filter( app.model.MetadataFile.table.c.hda_id==hda.id ).all():
                metadata_files.append( metadata_file )
        for lda in dataset.library_associations:
            for metadata_file in app.model.MetadataFile.filter( app.model.MetadataFile.table.c.lda_id==lda.id ).all():
                metadata_files.append( metadata_file )
        for metadata_file in metadata_files:
            print "# The following metadata files attached to associations of Dataset '%s' have been purged:" % dataset.id
            if not info_only:
                if remove_from_disk:
                    try:
                        os.unlink( metadata_file.file_name )
                    except Exception, e:
                        print "# Error, exception: %s caught attempting to purge metadata file %s\n" %( str( e ), metadata_file.file_name )
                    metadata_file.purged = True
                metadata_file.deleted = True
                #metadata_file.flush()
            print "%s" % metadata_file.file_name
        print
        dataset.deleted = True
        app.model.flush()

def _purge_dataset( dataset, remove_from_disk, info_only = False ):
    if dataset.deleted:
        try:
            if dataset.purgable and _dataset_is_deletable( dataset ):
                print "%s" % dataset.file_name
                if not info_only:
                    # Remove files from disk and update the database
                    if remove_from_disk:
                        # TODO: should permissions on the dataset be deleted here?
                        os.unlink( dataset.file_name )
                        # Remove associated extra files from disk if they exist
                        if dataset.extra_files_path and os.path.exists( dataset.extra_files_path ):
                            shutil.rmtree( dataset.extra_files_path ) #we need to delete the directory and its contents; os.unlink would always fail on a directory
                    dataset.purged = True
                    dataset.flush()
            else:
                print "# This dataset (%i) is not purgable, the file (%s) will not be removed.\n" % ( dataset.id, dataset.file_name )
        except OSError, exc:
            print "# Error, file has already been removed: %s" % str( exc )
            dataset.purged = True
            dataset.flush()
        except Exception, exc:
            print "# Error, exception: %s caught attempting to purge %s\n" %( str( exc ), dataset.file_name )
    else:
        print "# Error: '%s' has not previously been deleted, so it cannot be purged\n" % dataset.file_name
    print ""

def _purge_folder( folder, app, remove_from_disk, info_only = False ):
    """Purges a folder and its contents, recursively"""
    for ld in folder.datasets:
        ld.deleted = True
        for ldda in [ld.library_dataset_dataset_association] + ld.expired_datasets:
            _purge_dataset_instance( ldda, app, remove_from_disk, info_only = info_only ) #mark a DatasetInstance as deleted, clear associated files, and mark the Dataset as deleted if it is deletable
    for sub_folder in folder.folders:
        _purge_folder( sub_folder, app, remove_from_disk, info_only = info_only )
    if not info_only:
        # TODO: should the folder permissions be deleted here?
        folder.purged = True
        folder.flush()

class CleanupDatasetsApplication( object ):
    """Encapsulates the state of a Universe application"""
    def __init__( self, database_connection=None, file_path=None ):
        print >> sys.stderr, "python path is: " + ", ".join( sys.path )
        if database_connection is None:
            raise Exception( "CleanupDatasetsApplication requires a database_connection value" )
        if file_path is None:
            raise Exception( "CleanupDatasetsApplication requires a file_path value" )
        self.database_connection = database_connection
        self.file_path = file_path
        # Setup the database engine and ORM
        self.model = galaxy.model.mapping.init( self.file_path, self.database_connection, engine_options={}, create_tables=False )
    @property
    def sa_session( self ):
        """
        Returns a SQLAlchemy session -- currently just gets the current
        session from the threadlocal session context, but this is provided
        to allow migration toward a more SQLAlchemy 0.4 style of use.
        """
        return self.model.context.current

if __name__ == "__main__": main()
