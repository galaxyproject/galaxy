"""
objectstore package, abstraction for storing blobs of data for use in Galaxy,
all providers ensure that data can be accessed on the filesystem for running
tools
"""

import os
import time
import shutil
import logging
import threading
import subprocess
import multiprocessing
from datetime import datetime

from galaxy import util
from galaxy.jobs import Sleeper
from galaxy.model import directory_hash_id
from galaxy.objectstore.s3_multipart_upload import multipart_upload

from boto.s3.key import Key
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError

log = logging.getLogger( __name__ )
logging.getLogger('boto').setLevel(logging.INFO) # Otherwise boto is quite noisy


class ObjectNotFound(Exception):
    """ Accessed object was not found """
    pass


class ObjectStore(object):
    """
    ObjectStore abstract interface
    """
    def __init__(self):
        self.running = True
    
    def shutdown(self):
        self.running = False
    
    def exists(self, dataset_id, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Returns True if the object identified by `dataset_id` exists in this 
        file store, False otherwise.
        
        FIELD DESCRIPTIONS (these apply to all the methods in this class):
        :type dataset_id: int
        :param dataset_id: Galaxy-assigned database ID of the dataset to be checked.
        
        :type dir_only: bool
        :param dir_only: If True, check only the path where the file
                         identified by `dataset_id` should be located, not the
                         dataset itself. This option applies to `extra_dir`
                         argument as well.
        
        :type extra_dir: string
        :param extra_dir: Append `extra_dir` to the directory structure where
                          the dataset identified by `dataset_id` should be located.
                          (e.g., 000/extra_dir/dataset_id)
        
        :type extra_dir_at_root: bool
        :param extra_dir_at_root: Applicable only if `extra_dir` is set.
                                  If True, the `extra_dir` argument is placed at
                                  root of the created directory structure rather
                                  than at the end (e.g., extra_dir/000/dataset_id
                                  vs. 000/extra_dir/dataset_id)
        
        :type alt_name: string
        :param alt_name: Use this name as the alternative name for the created
                         dataset rather than the default.
        """
        raise NotImplementedError()
    
    def file_ready(self, dataset_id, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """ A helper method that checks if a file corresponding to a dataset 
        is ready and available to be used. Return True if so, False otherwise."""
        return True
    
    def create(self, dataset_id, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Mark the object identified by `dataset_id` as existing in the store, but
        with no content. This method will create a proper directory structure for
        the file if the directory does not already exist.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()
    
    def empty(self, dataset_id, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Test if the object identified by `dataset_id` has content.
        If the object does not exist raises `ObjectNotFound`.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()
    
    def size(self, dataset_id, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Return size of the object identified by `dataset_id`.
        If the object does not exist, return 0.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()
    
    def delete(self, dataset_id, entire_dir=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Deletes the object identified by `dataset_id`.
        See `exists` method for the description of other fields.
        :type entire_dir: bool
        :param entire_dir: If True, delete the entire directory pointed to by 
                           extra_dir. For safety reasons, this option applies
                           only for and in conjunction with the extra_dir option.
        """
        raise NotImplementedError()
    
    def get_data(self, dataset_id, start=0, count=-1, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Fetch `count` bytes of data starting at offset `start` from the
        object identified uniquely by `dataset_id`.
        If the object does not exist raises `ObjectNotFound`.
        See `exists` method for the description of other fields.
        
        :type start: int
        :param start: Set the position to start reading the dataset file
        
        :type count: int
        :param count: Read at most `count` bytes from the dataset
        """
        raise NotImplementedError()
    
    def get_filename(self, dataset_id, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Get the expected filename (including the absolute path) which can be used
        to access the contents of the object uniquely identified by `dataset_id`.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()
    
    def update_from_file(self, dataset_id, extra_dir=None, extra_dir_at_root=False, alt_name=None, filename=None, create=False):
        """
        Inform the store that the file associated with the object has been
        updated. If `filename` is provided, update from that file instead
        of the default.
        If the object does not exist raises `ObjectNotFound`.
        See `exists` method for the description of other fields.
        
        :type filename: string
        :param filename: Use file pointed to by `filename` as the source for 
                         updating the dataset identified by `dataset_id`
        
        :type create: bool
        :param create: If True and the default dataset does not exist, create it first.
        """
        raise NotImplementedError()
    
    def get_object_url(self, dataset_id, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        If the store supports direct URL access, return a URL. Otherwise return
        None.
        Note: need to be careful to to bypass dataset security with this.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()
    
    ## def get_staging_command( id ):
    ##     """
    ##     Return a shell command that can be prepended to the job script to stage the
    ##     dataset -- runs on worker nodes.
    ##
    ##     Note: not sure about the interface here. Should this return a filename, command
    ##     tuple? Is this even a good idea, seems very useful for S3, other object stores?
    ##     """


class DiskObjectStore(ObjectStore):
    """
    Standard Galaxy object store, stores objects in files under a specific
    directory on disk.
    """
    def __init__(self, app):
        super(DiskObjectStore, self).__init__()
        self.file_path = app.config.file_path
    
    def _get_filename(self, dataset_id, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """Class method that returns the absolute path for the file corresponding
        to the `dataset_id` regardless of whether the file exists. 
        """
        path = self._construct_path(dataset_id, dir_only=dir_only, extra_dir=extra_dir, extra_dir_at_root=extra_dir_at_root, alt_name=alt_name, old_style=True)
        # For backward compatibility, check the old style root path first; otherwise, 
        # construct hashed path
        if not os.path.exists(path):
            return self._construct_path(dataset_id, dir_only=dir_only, extra_dir=extra_dir, extra_dir_at_root=extra_dir_at_root, alt_name=alt_name)
    
    def _construct_path(self, dataset_id, old_style=False, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """ Construct the expected absolute path for accessing the object
            identified by `dataset_id`.
        
        :type dir_only: bool
        :param dir_only: If True, return only the absolute path where the file
                         identified by `dataset_id` should be located
        
        :type extra_dir: string
        :param extra_dir: Append the value of this parameter to the expected path
                          used to access the object identified by `dataset_id`
                          (e.g., /files/000/<extra_dir>/dataset_10.dat).
        
        :type alt_name: string
        :param alt_name: Use this name as the alternative name for the returned
                         dataset rather than the default.
        
        :type old_style: bool
        param old_style: This option is used for backward compatibility. If True
                         the composed directory structure does not include a hash id
                         (e.g., /files/dataset_10.dat (old) vs. /files/000/dataset_10.dat (new))
        """
        if old_style:
            if extra_dir is not None:
                path = os.path.join(self.file_path, extra_dir)
            else:
                path = self.file_path
        else:
            rel_path = os.path.join(*directory_hash_id(dataset_id))
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)
            path = os.path.join(self.file_path, rel_path)
        if not dir_only:
            path = os.path.join(path, alt_name if alt_name else "dataset_%s.dat" % dataset_id)
        return os.path.abspath(path)
    
    def exists(self, dataset_id, **kwargs):
        path = self._construct_path(dataset_id, old_style=True, **kwargs)
        # For backward compatibility, check root path first; otherwise, construct 
        # and check hashed path
        if not os.path.exists(path):
            path = self._construct_path(dataset_id, **kwargs)
        return os.path.exists(path)
    
    def create(self, dataset_id, **kwargs):
        if not self.exists(dataset_id, **kwargs):
            # Pull out locally used fields
            extra_dir = kwargs.get('extra_dir', None)
            extra_dir_at_root = kwargs.get('extra_dir_at_root', False)
            dir_only = kwargs.get('dir_only', False)
            alt_name = kwargs.get('alt_name', None)
            # Construct hashed path
            path = os.path.join(*directory_hash_id(dataset_id))
            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    path = os.path.join(extra_dir, path)
                else:
                    path = os.path.join(path, extra_dir)
            # Combine the constructted path with the root dir for all files
            path = os.path.join(self.file_path, path)
            # Create directory if it does not exist
            if not os.path.exists(path):
                os.makedirs(path)
            if not dir_only:
                path = os.path.join(path, alt_name if alt_name else "dataset_%s.dat" % dataset_id)
                open(path, 'w').close() 
    
    def empty(self, dataset_id, **kwargs):
        return os.path.getsize(self.get_filename(dataset_id, **kwargs)) > 0
    
    def size(self, dataset_id, **kwargs):
        if self.exists(dataset_id, **kwargs):
            try:
                return os.path.getsize(self.get_filename(dataset_id, **kwargs))
            except OSError:
                return 0
        else:
            return 0
    
    def delete(self, dataset_id, entire_dir=False, **kwargs):
        path = self.get_filename(dataset_id, **kwargs)
        extra_dir = kwargs.get('extra_dir', None)
        try:
            if entire_dir and extra_dir:
                shutil.rmtree(path)
                return True
            if self.exists(dataset_id, **kwargs):
                    os.remove(path)
                    return True
        except OSError, ex:
            log.critical('%s delete error %s' % (self._get_filename(dataset_id, **kwargs), ex))
        return False
    
    def get_data(self, dataset_id, start=0, count=-1, **kwargs):
        data_file = open(self.get_filename(dataset_id, **kwargs), 'r')
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content
    
    def get_filename(self, dataset_id, **kwargs):
        path = self._construct_path(dataset_id, old_style=True, **kwargs)
        # For backward compatibility, check root path first; otherwise, construct 
        # and check hashed path
        if os.path.exists(path):
            return path
        else:
            path = self._construct_path(dataset_id, **kwargs)
        print "Checking it %s exists: %s" %(path, os.path.exists(path))
        if os.path.exists(path):
            return path
        else:
            raise ObjectNotFound()
    
    def update_from_file(self, dataset_id, file_name=None, create=False, **kwargs):
        """ `create` parameter is not used in this implementation """
        if create:
            self.create(dataset_id, **kwargs)
        if file_name and self.exists(dataset_id, **kwargs):
            try:
                shutil.copy(file_name, self.get_filename(dataset_id, **kwargs))
            except IOError, ex:
                log.critical('Error copying %s to %s: %s' % (file_name, 
                    self._get_filename(dataset_id, **kwargs), ex))
    
    def get_object_url(self, dataset_id, **kwargs):
        return None
    


class CachingObjectStore(ObjectStore):
    """
    Object store that uses a directory for caching files, but defers and writes
    back to another object store.
    """
    
    def __init__(self, path, backend):
        super(CachingObjectStore, self).__init__(self, path, backend)
    


class S3ObjectStore(ObjectStore):
    """
    Object store that stores objects as items in an AWS S3 bucket. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and S3.
    """
    def __init__(self, app):
        super(S3ObjectStore, self).__init__()
        self.app = app
        self.staging_path = self.app.config.file_path
        self.s3_conn = S3Connection()
        self.bucket = self._get_bucket(self.app.config.s3_bucket)
        self.use_rr = self.app.config.use_reduced_redundancy
        self.cache_size = self.app.config.object_store_cache_size * 1073741824 # Convert GBs to bytes
        self.transfer_progress = 0
        # Clean cache only if value is set in universe_wsgi.ini
        if self.cache_size != -1:
            # Helper for interruptable sleep
            self.sleeper = Sleeper()
            self.cache_monitor_thread = threading.Thread(target=self.__cache_monitor)
            self.cache_monitor_thread.start()
            log.info("Cache cleaner manager started")
    
    def __cache_monitor(self):
        time.sleep(2) # Wait for things to load before starting the monitor
        while self.running:
            total_size = 0
            # Is this going to be too expensive of an operation to be done frequently?
            file_list = []
            for dirpath, dirnames, filenames in os.walk(self.staging_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    file_size = os.path.getsize(fp)
                    total_size += file_size
                    # Get the time given file was last accessed
                    last_access_time = time.localtime(os.stat(fp)[7])
                    # Compose a tuple of the access time and the file path
                    file_tuple = last_access_time, fp, file_size
                    file_list.append(file_tuple)
            # Sort the file list (based on access time)
            file_list.sort()
            # Initiate cleaning once within 10% of the defined cache size?
            cache_limit = self.cache_size * 0.9
            if total_size > cache_limit:
                log.info("Initiating cache cleaning: current cache size: %s; clean until smaller than: %s" \
                    % (convert_bytes(total_size), convert_bytes(cache_limit)))
                # How much to delete? If simply deleting up to the cache-10% limit,
                # is likely to be deleting frequently and may run the risk of hitting
                # the limit - maybe delete additional #%?
                # For now, delete enough to leave at least 10% of the total cache free
                delete_this_much = total_size - cache_limit
                self.__clean_cache(file_list, delete_this_much)
            self.sleeper.sleep(30) # Test cache size every 30 seconds?
    
    def __clean_cache(self, file_list, delete_this_much):
        """ Keep deleting files from the file_list until the size of the deleted
        files is greater than the value in delete_this_much parameter.
        
        :type file_list: list
        :param file_list: List of candidate files that can be deleted. This method
            will start deleting files from the beginning of the list so the list
            should be sorted accordingly. The list must contains 3-element tuples,
            positioned as follows: position 0 holds file last accessed timestamp
            (as time.struct_time), position 1 holds file path, and position 2 has 
            file size (e.g., (<access time>, /mnt/data/dataset_1.dat), 472394)
        
        :type delete_this_much: int
        :param delete_this_much: Total size of files, in bytes, that should be deleted.
        """
        # Keep deleting datasets from file_list until deleted_amount does not
        # exceed delete_this_much; start deleting from the front of the file list,
        # which assumes the oldest files come first on the list.
        deleted_amount = 0
        for i, f in enumerate(file_list):
            if deleted_amount < delete_this_much:
                deleted_amount += f[2]
                os.remove(f[1])
                # Debugging code for printing deleted files' stats
                # folder, file_name = os.path.split(f[1])
                # file_date = time.strftime("%m/%d/%y %H:%M:%S", f[0])
                # log.debug("%s. %-25s %s, size %s (deleted %s/%s)" \
                #     % (i, file_name, convert_bytes(f[2]), file_date, \
                #     convert_bytes(deleted_amount), convert_bytes(delete_this_much)))
            else:
                log.debug("Cache cleaning done. Total space freed: %s" % convert_bytes(deleted_amount))
                return
    
    def _get_bucket(self, bucket_name):
        """ Sometimes a handle to a bucket is not established right away so try
        it a few times. Raise error is connection is not established. """
        for i in range(5):
            try:
                bucket = self.s3_conn.get_bucket(bucket_name)
                log.debug("Using S3 object store; got bucket '%s'" % bucket.name)
                return bucket
            except S3ResponseError: 
                log.debug("Could not get bucket '%s', attempt %s/5" % (bucket_name, i+1))
                time.sleep(2)
        # All the attempts have been exhausted and connection was not established,
        # raise error
        raise S3ResponseError
    
    def _fix_permissions(self, rel_path):
        """ Set permissions on rel_path"""
        for basedir, dirs, files in os.walk(rel_path):
            util.umask_fix_perms(basedir, self.app.config.umask, 0777, self.app.config.gid)
            for f in files:
                path = os.path.join(basedir, f)
                # Ignore symlinks
                if os.path.islink(path):
                    continue 
                util.umask_fix_perms( path, self.app.config.umask, 0666, self.app.config.gid )
    
    def _construct_path(self, dataset_id, dir_only=None, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        rel_path = os.path.join(*directory_hash_id(dataset_id))
        if extra_dir is not None:
            if extra_dir_at_root:
                rel_path = os.path.join(extra_dir, rel_path)
            else:
                rel_path = os.path.join(rel_path, extra_dir)
        # S3 folders are marked by having trailing '/' so add it now
        rel_path = '%s/' % rel_path
        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else "dataset_%s.dat" % dataset_id)
        return rel_path
    
    def _get_cache_path(self, rel_path):
        return os.path.abspath(os.path.join(self.staging_path, rel_path))
    
    def _get_transfer_progress(self):
        return self.transfer_progress
    
    def _get_size_in_s3(self, rel_path):
        try:
            key = self.bucket.get_key(rel_path)
            if key:
                return key.size
        except S3ResponseError, ex:
            log.error("Could not get size of key '%s' from S3: %s" % (rel_path, ex))
        except Exception, ex:
            log.error("Could not get reference to the key object '%s'; returning -1 for key size: %s" % (rel_path, ex))
        return -1
    
    def _key_exists(self, rel_path):
        exists = False
        try:
            # A hackish way of testing if the rel_path is a folder vs a file
            is_dir = rel_path[-1] == '/'
            if is_dir:
                rs = self.bucket.get_all_keys(prefix=rel_path)
                if len(rs) > 0:
                    exists = True
                else:
                    exists = False
            else:
                key = Key(self.bucket, rel_path)
                exists = key.exists()
        except S3ResponseError, ex:
            log.error("Trouble checking existence of S3 key '%s': %s" % (rel_path, ex))
            return False
        print "Checking if '%s' exists in S3: %s" % (rel_path, exists)
        if rel_path[0] == '/':
            raise
        return exists
    
    def _in_cache(self, rel_path):
        """ Check if the given dataset is in the local cache and return True if so. """
        # log.debug("------ Checking cache for rel_path %s" % rel_path)
        cache_path = self._get_cache_path(rel_path)
        exists = os.path.exists(cache_path)
        # print "Checking chache for %s; returning %s" % (cache_path, exists)
        return exists
        # EATODO: Part of checking if a file is in cache should be to ensure the 
        # size of the cached file matches that on S3. Once the upload tool explicitly
        # creates, this check sould be implemented- in the mean time, it's not
        # looking likely to be implementable reliably.
        # if os.path.exists(cache_path):
        #     # print "***1 %s exists" % cache_path
        #     if self._key_exists(rel_path):
        #         # print "***2 %s exists in S3" % rel_path
        #         # Make sure the size in cache is available in its entirety
        #         # print "File '%s' cache size: %s, S3 size: %s" % (cache_path, os.path.getsize(cache_path), self._get_size_in_s3(rel_path))
        #         if os.path.getsize(cache_path) == self._get_size_in_s3(rel_path):
        #             # print "***2.1 %s exists in S3 and the size is the same as in cache (in_cache=True)" % rel_path
        #             exists = True
        #         else:
        #             # print "***2.2 %s exists but differs in size from cache (in_cache=False)" % cache_path
        #             exists = False
        #     else:
        #         # Although not perfect decision making, this most likely means
        #         # that the file is currently being uploaded
        #         # print "***3 %s found in cache but not in S3 (in_cache=True)" % cache_path
        #         exists = True
        # else:
        #     # print "***4 %s does not exist (in_cache=False)" % cache_path
        #     exists = False
        # # print "Checking cache for %s; returning %s" % (cache_path, exists)
        # return exists
        # # return False
    
    def _pull_into_cache(self, rel_path):
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir))
        # Now pull in the file
        ok = self._download(rel_path)
        self._fix_permissions(self._get_cache_path(rel_path_dir))
        return ok
    
    def _transfer_cb(self, complete, total):
        self.transfer_progress += 10
        # print "Dataset transfer progress: %s" % self.transfer_progress
    
    def _download(self, rel_path):
        try:
            log.debug("Pulling key '%s' into cache to %s" % (rel_path, self._get_cache_path(rel_path)))
            key = self.bucket.get_key(rel_path)
            # Test is cache is large enough to hold the new file
            if key.size > self.cache_size:
                log.critical("File %s is larger (%s) than the cache size (%s). Cannot download." \
                    % (rel_path, key.size, self.cache_size))
                return False
            # Test if 'axel' is available for parallel download and pull the key into cache
            try:
                ret_code = subprocess.call('axel')
            except OSError:
                ret_code = 127
            if ret_code == 127:
                self.transfer_progress = 0 # Reset transfer progress counter
                key.get_contents_to_filename(self._get_cache_path(rel_path), cb=self._transfer_cb, num_cb=10)
                print "(ssss1) Pulled key '%s' into cache to %s" % (rel_path, self._get_cache_path(rel_path))
                return True
            else:
                ncores = multiprocessing.cpu_count()
                url = key.generate_url(7200)
                ret_code = subprocess.call("axel -a -n %s '%s'" % (ncores, url))
                if ret_code == 0:
                    print "(ssss2) Parallel pulled key '%s' into cache to %s" % (rel_path, self._get_cache_path(rel_path))
                    return True
        except S3ResponseError, ex:
            log.error("Problem downloading key '%s' from S3 bucket '%s': %s" % (rel_path, self.bucket.name, ex))
        return False
    
    def _push_to_s3(self, rel_path, source_file=None, from_string=None):
        """ 
        Push the file pointed to by `rel_path` to S3 naming the key `rel_path`. 
        If `source_file` is provided, push that file instead while still using 
        `rel_path` as the key name.
        If `from_string` is provided, set contents of the file to the value of
        the string
        """
        try:
            source_file = source_file if source_file else self._get_cache_path(rel_path)
            if os.path.exists(source_file):
                key = Key(self.bucket, rel_path)
                if from_string:
                    key.set_contents_from_string(from_string, reduced_redundancy=self.use_rr)
                    log.debug("Pushed data from string '%s' to key '%s'" % (from_string, rel_path))
                else:
                    start_time = datetime.now()
                    print "[%s] Pushing cache file '%s' to key '%s'" % (start_time, source_file, rel_path)
                    mb_size = os.path.getsize(source_file) / 1e6
                    if mb_size < 60:
                        self.transfer_progress = 0 # Reset transfer progress counter
                        key.set_contents_from_filename(source_file, reduced_redundancy=self.use_rr,
                            cb=self._transfer_cb, num_cb=10)
                    else:
                        multipart_upload(self.bucket, key.name, source_file, mb_size, use_rr=self.use_rr)
                        # self._multipart_upload(key.name, source_file, mb_size)
                    end_time = datetime.now()
                    print "Push ended at '%s'; it lasted '%s'" % (end_time, end_time-start_time)
                    log.debug("Pushed cache file '%s' to key '%s'" % (source_file, rel_path))
                return True
            else:
                log.error("Tried updating key '%s' from source file '%s', but source file does not exist."
                    % (rel_path, source_file))
        except S3ResponseError, ex:
            log.error("Trouble pushing S3 key '%s' from file '%s': %s" % (rel_path, source_file, ex))
        return False
    
    def file_ready(self, dataset_id, **kwargs):
        """ A helper method that checks if a file corresponding to a dataset 
        is ready and available to be used. Return True if so, False otherwise."""
        rel_path = self._construct_path(dataset_id, **kwargs)
        # Make sure the size in cache is available in its entirety
        if self._in_cache(rel_path) and os.path.getsize(self._get_cache_path(rel_path)) == self._get_size_in_s3(rel_path):
            return True
        return False
    
    def exists(self, dataset_id, **kwargs):
        in_cache = in_s3 = False
        rel_path = self._construct_path(dataset_id, **kwargs)
        # Check cache
        if self._in_cache(rel_path):
            in_cache = True
        # Check S3
        in_s3 = self._key_exists(rel_path)
        # log.debug("~~~~~~ File '%s' exists in cache: %s; in s3: %s" % (rel_path, in_cache, in_s3))
        # dir_only does not get synced so shortcut the decision
        dir_only = kwargs.get('dir_only', False)
        if dir_only:
            if in_cache or in_s3:
                return True
            else:
                return False
        # TODO: Sync should probably not be done here. Add this to an async upload stack?
        if in_cache and not in_s3:
            self._push_to_s3(rel_path, source_file=self._get_cache_path(rel_path))
            return True
        elif in_s3:
            return True
        else:
            return False
    
    def create(self, dataset_id, **kwargs):
        if not self.exists(dataset_id, **kwargs):
            print "S3 OS creating a dataset with ID %s" % dataset_id
            # Pull out locally used fields
            extra_dir = kwargs.get('extra_dir', None)
            extra_dir_at_root = kwargs.get('extra_dir_at_root', False)
            dir_only = kwargs.get('dir_only', False)
            alt_name = kwargs.get('alt_name', None)
            # print "---- Processing: %s; %s" % (alt_name, locals())
            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(dataset_id))
            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)
            # Create given directory in cache
            cache_dir = os.path.join(self.staging_path, rel_path)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            # Although not really necessary to create S3 folders (because S3 has
            # flat namespace), do so for consistency with the regular file system
            # S3 folders are marked by having trailing '/' so add it now
            # s3_dir = '%s/' % rel_path
            # self._push_to_s3(s3_dir, from_string='')
            # If instructed, create the dataset in cache & in S3
            if not dir_only:
                rel_path = os.path.join(rel_path, alt_name if alt_name else "dataset_%s.dat" % dataset_id)
                open(os.path.join(self.staging_path, rel_path), 'w').close()
                self._push_to_s3(rel_path, from_string='')
    
    def empty(self, dataset_id, **kwargs):
        if self.exists(dataset_id, **kwargs):
            return bool(self.size(dataset_id, **kwargs) > 0)
        else:
            raise ObjectNotFound()
    
    def size(self, dataset_id, **kwargs):
        rel_path = self._construct_path(dataset_id, **kwargs)
        if self._in_cache(rel_path):
            try:
                return os.path.getsize(self._get_cache_path(rel_path))
            except OSError, ex:
                log.info("Could not get size of file '%s' in local cache, will try S3. Error: %s" % (rel_path, ex))
        elif self.exists(dataset_id, **kwargs):
            return self._get_size_in_s3(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size" % rel_path)
        return 0
    
    def delete(self, dataset_id, entire_dir=False, **kwargs):
        rel_path = self._construct_path(dataset_id, **kwargs)
        extra_dir = kwargs.get('extra_dir', None)
        try:
            # For the case of extra_files, because we don't have a reference to
            # individual files/keys we need to remove the entire directory structure
            # with all the files in it. This is easy for the local file system,
            # but requires iterating through each individual key in S3 and deleing it.
            if entire_dir and extra_dir:
                shutil.rmtree(self._get_cache_path(rel_path))
                rs = self.bucket.get_all_keys(prefix=rel_path)
                for key in rs:
                    log.debug("Deleting key %s" % key.name)
                    key.delete()
                return True
            else:
                # Delete from cache first
                os.unlink(self._get_cache_path(rel_path))
                # Delete from S3 as well
                if self._key_exists(rel_path):
                        key = Key(self.bucket, rel_path)
                        log.debug("Deleting key %s" % key.name)
                        key.delete()
                        return True
        except S3ResponseError, ex:
            log.error("Could not delete key '%s' from S3: %s" % (rel_path, ex))
        except OSError, ex:
            log.error('%s delete error %s' % (self._get_filename(dataset_id, **kwargs), ex))
        return False
    
    def get_data(self, dataset_id, start=0, count=-1, **kwargs):
        rel_path = self._construct_path(dataset_id, **kwargs)
        # Check cache first and get file if not there
        if not self._in_cache(rel_path):
            self._pull_into_cache(rel_path)
        else:
            print "(cccc) Getting '%s' from cache" % self._get_cache_path(rel_path)
        # Read the file content from cache
        data_file = open(self._get_cache_path(rel_path), 'r')
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content
    
    def get_filename(self, dataset_id, **kwargs):
        print "S3 get_filename for dataset: %s" % dataset_id
        dir_only = kwargs.get('dir_only', False)
        rel_path = self._construct_path(dataset_id, **kwargs)
        cache_path = self._get_cache_path(rel_path)
        # S3 does not recognize directories as files so cannot check if those exist.
        # So, if checking dir only, ensure given dir exists in cache and return
        # the expected cache path.
        # dir_only = kwargs.get('dir_only', False)
        # if dir_only:
        #     if not os.path.exists(cache_path):
        #         os.makedirs(cache_path)
        #     return cache_path
        # Check if the file exists in the cache first
        if self._in_cache(rel_path):
            return cache_path
        # Check if the file exists in persistent storage and, if it does, pull it into cache
        elif self.exists(dataset_id, **kwargs):
            if dir_only: # Directories do not get pulled into cache
                return cache_path
            else:
                if self._pull_into_cache(rel_path):
                    return cache_path
        # For the case of retrieving a directory only, return the expected path
        # even if it does not exist.
        # if dir_only:
        #     return cache_path
        raise ObjectNotFound()
        # return cache_path # Until the upload tool does not explicitly create the dataset, return expected path
    
    def update_from_file(self, dataset_id, file_name=None, create=False, **kwargs): 
        if create:
            self.create(dataset_id, **kwargs)
        if self.exists(dataset_id, **kwargs):
            rel_path = self._construct_path(dataset_id, **kwargs)
            # Chose whether to use the dataset file itself or an alternate file
            if file_name:
                source_file = os.path.abspath(file_name)
                # Copy into cache
                cache_file = self._get_cache_path(rel_path)
                try:
                    # FIXME? Should this be a `move`?
                    shutil.copy2(source_file, cache_file)
                    self._fix_permissions(cache_file)
                except OSError, ex:
                    log.error("Trouble copying source file '%s' to cache '%s': %s" % (source_file, cache_file, ex))
            else:
                source_file = self._get_cache_path(rel_path)
            # Update the file on S3
            self._push_to_s3(rel_path, source_file)
        else:
            raise ObjectNotFound()
    
    def get_object_url(self, dataset_id, **kwargs):
        if self.exists(dataset_id, **kwargs):
            rel_path = self._construct_path(dataset_id, **kwargs)
            try:
                key = Key(self.bucket, rel_path)
                return key.generate_url(expires_in = 86400) # 24hrs
            except S3ResponseError, ex:
                log.warning("Trouble generating URL for dataset '%s': %s" % (rel_path, ex))
        return None
    


class HierarchicalObjectStore(ObjectStore):
    """
    ObjectStore that defers to a list of backends, for getting objects the
    first store where the object exists is used, objects are always created
    in the first store.
    """
    
    def __init__(self, backends=[]):
        super(HierarchicalObjectStore, self).__init__()
    

def build_object_store_from_config(app):
    """ Depending on the configuration setting, invoke the appropriate object store
    """
    store = app.config.object_store
    if store == 'disk':
        return DiskObjectStore(app=app)
    elif store == 's3':
        os.environ['AWS_ACCESS_KEY_ID'] = app.config.aws_access_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = app.config.aws_secret_key
        return S3ObjectStore(app=app)
    elif store == 'hierarchical':
        return HierarchicalObjectStore()

def convert_bytes(bytes):
    """ A helper function used for pretty printing disk usage """
    if bytes is None:
        bytes = 0
    bytes = float(bytes)
    
    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fTB' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fGB' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fMB' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fKB' % kilobytes
    else:
        size = '%.2fb' % bytes
    return size
