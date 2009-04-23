import sys, logging, os, time

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

from migrate import migrate_engine
from sqlalchemy import and_

# load existing galaxy model, we are only changing data
import galaxy.model
from galaxy.model import mapping
model = mapping.init( galaxy.model.Dataset.file_path, str( migrate_engine.url ) )

def __guess_dataset_by_filename( filename ):
    """Return a guessed dataset by filename"""
    try:
        fields = os.path.split( filename )
        if fields:
            if fields[-1].startswith( 'dataset_' ) and fields[-1].endswith( '.dat' ): #dataset_%d.dat
                return model.Dataset.get( int( fields[-1][ len( 'dataset_' ): -len( '.dat' ) ] ) )
    except:
        pass #some parsing error, we can't guess Dataset
    return None

def upgrade():
    log.debug( "Fixing a discrepancy concerning deleted shared history items." )
    affected_items = 0
    start_time = time.time()
    for dataset in model.Dataset.filter( and_( model.Dataset.c.deleted == True, model.Dataset.c.purged == False ) ).all():
        for dataset_instance in dataset.history_associations + dataset.library_associations:
            if not dataset_instance.deleted:
                dataset.deleted = False
                if dataset.file_size in [ None, 0 ]:
                    dataset.set_size() #Restore filesize
                affected_items += 1
                break
    galaxy.model.mapping.Session.flush()
    log.debug( "%i items affected, and restored." % ( affected_items ) )
    log.debug( "Time elapsed: %s" % ( time.time() - start_time ) )
    
    #fix share before hda
    log.debug( "Fixing a discrepancy concerning cleaning up deleted history items shared before HDAs." )
    dataset_by_filename = {}
    changed_associations = 0
    start_time = time.time()
    for dataset in model.Dataset.filter( model.Dataset.external_filename.like( '%dataset_%.dat' ) ).all():
        if dataset.file_name in dataset_by_filename:
            guessed_dataset = dataset_by_filename[ dataset.file_name ]
        else:
            guessed_dataset = __guess_dataset_by_filename( dataset.file_name )
            if guessed_dataset and dataset.file_name != guessed_dataset.file_name:#not os.path.samefile( dataset.file_name, guessed_dataset.file_name ):
                guessed_dataset = None
            dataset_by_filename[ dataset.file_name ] = guessed_dataset
        
        if guessed_dataset is not None and guessed_dataset.id != dataset.id: #could we have a self referential dataset?
            for dataset_instance in dataset.history_associations + dataset.library_associations:
                dataset_instance.dataset = guessed_dataset
                changed_associations += 1
            #mark original Dataset as deleted and purged, it is no longer in use, but do not delete file_name contents
            dataset.deleted = True
            dataset.external_filename = "Dataset was result of share before HDA, and has been replaced: %s mapped to Dataset %s" % ( dataset.external_filename, guessed_dataset.id )
            dataset.purged = True #we don't really purge the file here, but we mark it as purged, since this dataset is now defunct
    galaxy.model.mapping.Session.flush()
    log.debug( "%i items affected, and restored." % ( changed_associations ) )
    log.debug( "Time elapsed: %s" % ( time.time() - start_time ) )

def downgrade():
    log.debug( "Downgrade is not possible." )
    
