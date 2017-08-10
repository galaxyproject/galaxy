"""
Object Store plugin for the Integrated Rule-Oriented Data Store (iRODS)

The module is named rods to avoid conflicting with the PyRods module, irods
"""

import logging
import os
import time

from posixpath import basename as path_basename
from posixpath import dirname as path_dirname
from posixpath import join as path_join

from galaxy.exceptions import ObjectInvalid, ObjectNotFound
from galaxy.util import safe_relpath

from ..objectstore import DiskObjectStore, local_extra_dirs

try:
    import irods
except ImportError:
    irods = None


IRODS_IMPORT_MESSAGE = ('The Python irods package is required to use this '
                        'feature, please install it')

log = logging.getLogger( __name__ )


class IRODSObjectStore( DiskObjectStore ):
    """
    Galaxy object store based on iRODS
    """
    def __init__( self, config, file_path=None, extra_dirs=None ):
        super( IRODSObjectStore, self ).__init__( config, file_path=file_path, extra_dirs=extra_dirs )
        assert irods is not None, IRODS_IMPORT_MESSAGE
        self.cache_path = config.object_store_cache_path
        self.default_resource = config.irods_default_resource or None

        # Connect to iRODS (AssertionErrors will be raised if anything goes wrong)
        self.rods_env, self.rods_conn = rods_connect()

        # if the root collection path in the config is unset or relative, try to use a sensible default
        if config.irods_root_collection_path is None or ( config.irods_root_collection_path is not None and not config.irods_root_collection_path.startswith( '/' ) ):
            rods_home = self.rods_env.rodsHome
            assert rods_home != '', "Unable to initialize iRODS Object Store: rodsHome cannot be determined and irods_root_collection_path in Galaxy config is unset or not absolute."
            if config.irods_root_collection_path is None:
                self.root_collection_path = path_join( rods_home, 'galaxy_data' )
            else:
                self.root_collection_path = path_join( rods_home, config.irods_root_collection_path )
        else:
            self.root_collection_path = config.irods_root_collection_path

        # will return a collection object regardless of whether it exists
        self.root_collection = irods.irodsCollection( self.rods_conn, self.root_collection_path )

        if self.root_collection.getId() == -1:
            log.warning( "iRODS root collection does not exist, will attempt to create: %s", self.root_collection_path )
            self.root_collection.upCollection()
            assert self.root_collection.createCollection( os.path.basename( self.root_collection_path ) ) == 0, "iRODS root collection creation failed: %s" % self.root_collection_path
            self.root_collection = irods.irodsCollection( self.rods_conn, self.root_collection_path )
            assert self.root_collection.getId() != -1, "iRODS root collection creation claimed success but still does not exist"

        if self.default_resource is None:
            self.default_resource = self.rods_env.rodsDefResource

        log.info( "iRODS data for this instance will be stored in collection: %s, resource: %s", self.root_collection_path, self.default_resource )

    def __get_rods_path( self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, strip_dat=True, **kwargs ):
        # extra_dir should never be constructed from provided data but just
        # make sure there are no shenannigans afoot
        if extra_dir and extra_dir != os.path.normpath(extra_dir):
            log.warning('extra_dir is not normalized: %s', extra_dir)
            raise ObjectInvalid("The requested object is invalid")
        # ensure that any parent directory references in alt_name would not
        # result in a path not contained in the directory path constructed here
        if alt_name:
            if not safe_relpath(alt_name):
                log.warning('alt_name would locate path outside dir: %s', alt_name)
                raise ObjectInvalid("The requested object is invalid")
            # alt_name can contain parent directory references, but iRODS will
            # not follow them, so if they are valid we normalize them out
            alt_name = os.path.normpath(alt_name)
        path = ""
        if extra_dir is not None:
            path = extra_dir

        # extra_dir_at_root is ignored - since the iRODS plugin does not use
        # the directory hash, there is only one level of subdirectory.

        if not dir_only:
            # the .dat extension is stripped when stored in iRODS
            # TODO: is the strip_dat kwarg the best way to implement this?
            if strip_dat and alt_name and alt_name.endswith( '.dat' ):
                alt_name = os.path.splitext( alt_name )[0]
            default_name = 'dataset_%s' % obj.id
            if not strip_dat:
                default_name += '.dat'
            path = path_join( path, alt_name if alt_name else default_name )

        path = path_join( self.root_collection_path, path )
        return path

    def __get_cache_path( self, obj, **kwargs ):
        # FIXME: does not handle collections
        # FIXME: collisions could occur here
        return os.path.join( self.cache_path, path_basename( self.__get_rods_path( obj, strip_dat=False, **kwargs ) ) )

    def __clean_cache_entry( self, obj, **kwargs ):
        # FIXME: does not handle collections
        try:
            os.unlink( self.__get_cache_path( obj, **kwargs ) )
        except OSError:
            # it is expected that we'll call this method a lot regardless of
            # whether we think the cached file exists
            pass

    def __get_rods_handle( self, obj, mode='r', **kwargs ):
        if kwargs.get( 'dir_only', False ):
            return irods.irodsCollection( self.rods_conn, self.__get_rods_path( obj, **kwargs ) )
        else:
            return irods.irodsOpen( self.rods_conn, self.__get_rods_path( obj, **kwargs ), mode )

    def __mkcolls( self, rods_path ):
        """
        An os.makedirs() for iRODS collections.  `rods_path` is the desired collection to create.
        """
        assert rods_path.startswith( self.root_collection_path + '/' ), '__mkcolls(): Creating collections outside the root collection is not allowed (requested path was: %s)' % rods_path
        mkcolls = []
        c = irods.irodsCollection( self.rods_conn, rods_path )
        while c.getId() == -1:
            assert c.getCollName().startswith( self.root_collection_path + '/' ), '__mkcolls(): Attempted to move above the root collection: %s' % c.getCollName()
            mkcolls.append( c.getCollName() )
            c.upCollection()
        for collname in reversed( mkcolls ):
            log.debug( 'Creating collection %s' % collname )
            ci = irods.collInp_t()
            ci.collName = collname
            status = irods.rcCollCreate( self.rods_conn, ci )
            assert status == 0, '__mkcolls(): Failed to create collection: %s' % collname

    @local_extra_dirs
    def exists( self, obj, **kwargs ):
        doi = irods.dataObjInp_t()
        doi.objPath = self.__get_rods_path( obj, **kwargs )
        log.debug( 'exists(): checking: %s', doi.objPath )
        return irods.rcObjStat( self.rods_conn, doi ) is not None

    @local_extra_dirs
    def create(self, obj, **kwargs):
        if not self.exists( obj, **kwargs ):
            rods_path = self.__get_rods_path( obj, **kwargs )
            log.debug( 'create(): %s', rods_path )
            dir_only = kwargs.get( 'dir_only', False )
            # short circuit collection creation since most of the time it will
            # be the root collection which already exists
            collection_path = rods_path if dir_only else path_dirname( rods_path )
            if collection_path != self.root_collection_path:
                self.__mkcolls( collection_path )
            if not dir_only:
                # rcDataObjCreate is used instead of the irodsOpen wrapper so
                # that we can prevent overwriting
                doi = irods.dataObjInp_t()
                doi.objPath = rods_path
                doi.createMode = 0o640
                doi.dataSize = 0  # 0 actually means "unknown", although literally 0 would be preferable
                irods.addKeyVal( doi.condInput, irods.DEST_RESC_NAME_KW, self.default_resource )
                status = irods.rcDataObjCreate( self.rods_conn, doi )
                assert status >= 0, 'create(): rcDataObjCreate() failed: %s: %s: %s' % ( rods_path, status, irods.strerror( status ) )

    @local_extra_dirs
    def empty( self, obj, **kwargs ):
        assert 'dir_only' not in kwargs, 'empty(): `dir_only` parameter is invalid here'
        h = self.__get_rods_handle( obj, **kwargs )
        try:
            return h.getSize() == 0
        except AttributeError:
            # h is None
            raise ObjectNotFound()

    def size( self, obj, **kwargs ):
        assert 'dir_only' not in kwargs, 'size(): `dir_only` parameter is invalid here'
        h = self.__get_rods_handle( obj, **kwargs )
        try:
            return h.getSize()
        except AttributeError:
            # h is None
            return 0

    @local_extra_dirs
    def delete( self, obj, entire_dir=False, **kwargs ):
        assert 'dir_only' not in kwargs, 'delete(): `dir_only` parameter is invalid here'
        rods_path = self.__get_rods_path( obj, **kwargs )
        # __get_rods_path prepends self.root_collection_path but we are going
        # to ensure that it's valid anyway for safety's sake
        assert rods_path.startswith( self.root_collection_path + '/' ), 'ERROR: attempt to delete object outside root collection (path was: %s)' % rods_path
        if entire_dir:
            # TODO
            raise NotImplementedError()
        h = self.__get_rods_handle( obj, **kwargs )
        try:
            # note: PyRods' irodsFile.delete() does not set force
            status = h.delete()
            assert status == 0, '%d: %s' % ( status, irods.strerror( status ) )
            return True
        except AttributeError:
            log.warning( 'delete(): operation failed: object does not exist: %s', rods_path )
        except AssertionError as e:
            # delete() does not raise on deletion failure
            log.error( 'delete(): operation failed: %s', e )
        finally:
            # remove the cached entry (finally is executed even when the try
            # contains a return)
            self.__clean_cache_entry( self, obj, **kwargs )
        return False

    @local_extra_dirs
    def get_data( self, obj, start=0, count=-1, **kwargs ):
        log.debug( 'get_data(): %s' )
        h = self.__get_rods_handle( obj, **kwargs )
        try:
            h.seek( start )
        except AttributeError:
            raise ObjectNotFound()
        if count == -1:
            return h.read()
        else:
            return h.read( count )
        # TODO: make sure implicit close is okay, DiskObjectStore actually
        # reads data into a var, closes, and returns the var

    @local_extra_dirs
    def get_filename( self, obj, **kwargs ):
        log.debug( "get_filename(): called on %s %s. For better performance, avoid this method and use get_data() instead.", obj.__class__.__name__, obj.id )
        cached_path = self.__get_cache_path( obj, **kwargs )

        if not self.exists( obj, **kwargs ):
            raise ObjectNotFound()

        # TODO: implement or define whether dir_only is valid
        if 'dir_only' in kwargs:
            raise NotImplementedError()

        # cache hit
        if os.path.exists( cached_path ):
            return os.path.abspath( cached_path )

        # cache miss
        # TODO: thread this
        incoming_path = os.path.join( os.path.dirname( cached_path ), "__incoming_%s" % os.path.basename( cached_path ) )
        doi = irods.dataObjInp_t()
        doi.objPath = self.__get_rods_path( obj, **kwargs )
        doi.dataSize = 0  # TODO: does this affect performance? should we get size?
        doi.numThreads = 0
        # TODO: might want to VERIFY_CHKSUM_KW
        log.debug( 'get_filename(): caching %s to %s', doi.objPath, incoming_path )

        # do the iget
        status = irods.rcDataObjGet( self.rods_conn, doi, incoming_path )

        # if incoming already exists, we'll wait for another process or thread
        # to finish caching
        if status != irods.OVERWRITE_WITHOUT_FORCE_FLAG:
            assert status == 0, 'get_filename(): iget %s failed (%s): %s' % ( doi.objPath, status, irods.strerror( status ) )
            # POSIX rename is atomic
            # TODO: rename without clobbering
            os.rename( incoming_path, cached_path )
            log.debug( 'get_filename(): cached %s to %s', doi.objPath, cached_path )

        # another process or thread is caching, wait for it
        while not os.path.exists( cached_path ):
            # TODO: force restart after mod time > some configurable, or
            # otherwise deal with this potential deadlock and interrupted
            # transfers
            time.sleep( 5 )
            log.debug( "get_filename(): waiting on incoming '%s' for %s %s", incoming_path, obj.__class__.__name__, obj.id )

        return os.path.abspath( cached_path )

    @local_extra_dirs
    def update_from_file(self, obj, file_name=None, create=False, **kwargs):
        assert 'dir_only' not in kwargs, 'update_from_file(): `dir_only` parameter is invalid here'

        # do not create if not requested
        if create and not self.exists( obj, **kwargs ):
            raise ObjectNotFound()

        if file_name is None:
            file_name = self.__get_cache_path( obj, **kwargs )

        # put will create if necessary
        doi = irods.dataObjInp_t()
        doi.objPath = self.__get_rods_path( obj, **kwargs )
        doi.createMode = 0o640
        doi.dataSize = os.stat( file_name ).st_size
        doi.numThreads = 0
        irods.addKeyVal( doi.condInput, irods.DEST_RESC_NAME_KW, self.default_resource )
        irods.addKeyVal( doi.condInput, irods.FORCE_FLAG_KW, '' )
        # TODO: might want to VERIFY_CHKSUM_KW
        log.debug( 'update_from_file(): updating %s to %s', file_name, doi.objPath )

        # do the iput
        status = irods.rcDataObjPut( self.rods_conn, doi, file_name )
        assert status == 0, 'update_from_file(): iput %s failed (%s): %s' % ( doi.objPath, status, irods.strerror( status ) )

    def get_object_url(self, obj, **kwargs):
        return None

    def get_store_usage_percent(self):
        return 0.0


# monkeypatch an strerror method into the irods module
def _rods_strerror( errno ):
    """
    The missing `strerror` for iRODS error codes
    """
    if not hasattr( irods, '__rods_strerror_map' ):
        irods.__rods_strerror_map = {}
        for name in dir( irods ):
            v = getattr( irods, name )
            if type( v ) == int and v < 0:
                irods.__rods_strerror_map[ v ] = name
    return irods.__rods_strerror_map.get( errno, 'GALAXY_NO_ERRNO_MAPPING_FOUND' )


if irods is not None:
    irods.strerror = _rods_strerror


def rods_connect():
    """
    A basic iRODS connection mechanism that connects using the current iRODS
    environment
    """
    status, env = irods.getRodsEnv()
    assert status == 0, 'connect(): getRodsEnv() failed (%s): %s' % ( status, irods.strerror( status ) )
    conn, err = irods.rcConnect( env.rodsHost,
                                 env.rodsPort,
                                 env.rodsUserName,
                                 env.rodsZone )
    assert err.status == 0, 'connect(): rcConnect() failed (%s): %s' % ( err.status, err.msg )
    status, pw = irods.obfGetPw()
    assert status == 0, 'connect(): getting password with obfGetPw() failed (%s): %s' % ( status, irods.strerror( status ) )
    status = irods.clientLoginWithObfPassword( conn, pw )
    assert status == 0, 'connect(): logging in with clientLoginWithObfPassword() failed (%s): %s' % ( status, irods.strerror( status ) )
    return env, conn
