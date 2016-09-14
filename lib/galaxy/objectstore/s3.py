"""
Object Store plugin for the Amazon Simple Storage Service (S3)
"""

import logging
import multiprocessing
import os
import shutil
import subprocess
import threading
import time

from datetime import datetime

from galaxy.exceptions import ObjectInvalid, ObjectNotFound
from galaxy.util import (
    directory_hash_id,
    safe_relpath,
    string_as_bool,
    umask_fix_perms,
)
from galaxy.util.sleeper import Sleeper

from .s3_multipart_upload import multipart_upload
from ..objectstore import convert_bytes, ObjectStore

try:
    # Imports are done this way to allow objectstore code to be used outside of Galaxy.
    import boto

    from boto.exception import S3ResponseError
    from boto.s3.key import Key
    from boto.s3.connection import S3Connection
except ImportError:
    boto = None

NO_BOTO_ERROR_MESSAGE = ("S3/Swift object store configured, but no boto dependency available."
                         "Please install and properly configure boto or modify object store configuration.")

log = logging.getLogger( __name__ )
logging.getLogger('boto').setLevel(logging.INFO)  # Otherwise boto is quite noisy


class S3ObjectStore(ObjectStore):
    """
    Object store that stores objects as items in an AWS S3 bucket. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and S3.
    """
    def __init__(self, config, config_xml):
        if boto is None:
            raise Exception(NO_BOTO_ERROR_MESSAGE)
        super(S3ObjectStore, self).__init__(config)
        self.staging_path = self.config.file_path
        self.transfer_progress = 0
        self._parse_config_xml(config_xml)
        self._configure_connection()
        self.bucket = self._get_bucket(self.bucket)
        # Clean cache only if value is set in galaxy.ini
        if self.cache_size != -1:
            # Convert GBs to bytes for comparison
            self.cache_size = self.cache_size * 1073741824
            # Helper for interruptable sleep
            self.sleeper = Sleeper()
            self.cache_monitor_thread = threading.Thread(target=self.__cache_monitor)
            self.cache_monitor_thread.start()
            log.info("Cache cleaner manager started")
        # Test if 'axel' is available for parallel download and pull the key into cache
        try:
            subprocess.call('axel')
            self.use_axel = True
        except OSError:
            self.use_axel = False

    def _configure_connection(self):
        log.debug("Configuring S3 Connection")
        self.conn = S3Connection(self.access_key, self.secret_key)

    def _parse_config_xml(self, config_xml):
        try:
            a_xml = config_xml.findall('auth')[0]
            self.access_key = a_xml.get('access_key')
            self.secret_key = a_xml.get('secret_key')
            b_xml = config_xml.findall('bucket')[0]
            self.bucket = b_xml.get('name')
            self.use_rr = string_as_bool(b_xml.get('use_reduced_redundancy', "False"))
            self.max_chunk_size = int(b_xml.get('max_chunk_size', 250))
            cn_xml = config_xml.findall('connection')
            if not cn_xml:
                cn_xml = {}
            else:
                cn_xml = cn_xml[0]
            self.host = cn_xml.get('host', None)
            self.port = int(cn_xml.get('port', 6000))
            self.multipart = string_as_bool(cn_xml.get('multipart', 'True'))
            self.is_secure = string_as_bool(cn_xml.get('is_secure', 'True'))
            self.conn_path = cn_xml.get('conn_path', '/')
            c_xml = config_xml.findall('cache')[0]
            self.cache_size = float(c_xml.get('size', -1))
            self.staging_path = c_xml.get('path', self.config.object_store_cache_path)

            for d_xml in config_xml.findall('extra_dir'):
                self.extra_dirs[d_xml.get('type')] = d_xml.get('path')

            log.debug("Object cache dir:    %s", self.staging_path)
            log.debug("       job work dir: %s", self.extra_dirs['job_work'])

            # for multipart upload
            self.s3server = {'access_key': self.access_key,
                             'secret_key': self.secret_key,
                             'is_secure': self.is_secure,
                             'max_chunk_size': self.max_chunk_size,
                             'host': self.host,
                             'port': self.port,
                             'use_rr': self.use_rr,
                             'conn_path': self.conn_path}
        except Exception:
            # Toss it back up after logging, we can't continue loading at this point.
            log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
            raise

    def __cache_monitor(self):
        time.sleep(2)  # Wait for things to load before starting the monitor
        while self.running:
            total_size = 0
            # Is this going to be too expensive of an operation to be done frequently?
            file_list = []
            for dirpath, _, filenames in os.walk(self.staging_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    file_size = os.path.getsize(filepath)
                    total_size += file_size
                    # Get the time given file was last accessed
                    last_access_time = time.localtime(os.stat(filepath)[7])
                    # Compose a tuple of the access time and the file path
                    file_tuple = last_access_time, filepath, file_size
                    file_list.append(file_tuple)
            # Sort the file list (based on access time)
            file_list.sort()
            # Initiate cleaning once within 10% of the defined cache size?
            cache_limit = self.cache_size * 0.9
            if total_size > cache_limit:
                log.info("Initiating cache cleaning: current cache size: %s; clean until smaller than: %s",
                         convert_bytes(total_size), convert_bytes(cache_limit))
                # How much to delete? If simply deleting up to the cache-10% limit,
                # is likely to be deleting frequently and may run the risk of hitting
                # the limit - maybe delete additional #%?
                # For now, delete enough to leave at least 10% of the total cache free
                delete_this_much = total_size - cache_limit
                self.__clean_cache(file_list, delete_this_much)
            self.sleeper.sleep(30)  # Test cache size every 30 seconds?

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
        for entry in enumerate(file_list):
            if deleted_amount < delete_this_much:
                deleted_amount += entry[2]
                os.remove(entry[1])
                # Debugging code for printing deleted files' stats
                # folder, file_name = os.path.split(f[1])
                # file_date = time.strftime("%m/%d/%y %H:%M:%S", f[0])
                # log.debug("%s. %-25s %s, size %s (deleted %s/%s)" \
                #     % (i, file_name, convert_bytes(f[2]), file_date, \
                #     convert_bytes(deleted_amount), convert_bytes(delete_this_much)))
            else:
                log.debug("Cache cleaning done. Total space freed: %s", convert_bytes(deleted_amount))
                return

    def _get_bucket(self, bucket_name):
        """ Sometimes a handle to a bucket is not established right away so try
        it a few times. Raise error is connection is not established. """
        for i in range(5):
            try:
                bucket = self.conn.get_bucket(bucket_name)
                log.debug("Using cloud object store with bucket '%s'", bucket.name)
                return bucket
            except S3ResponseError:
                try:
                    log.debug("Bucket not found, creating s3 bucket with handle '%s'", bucket_name)
                    self.conn.create_bucket(bucket_name)
                except S3ResponseError:
                    log.exception("Could not get bucket '%s', attempt %s/5", bucket_name, i + 1)
                    time.sleep(2)
        # All the attempts have been exhausted and connection was not established,
        # raise error
        raise S3ResponseError

    def _fix_permissions(self, rel_path):
        """ Set permissions on rel_path"""
        for basedir, _, files in os.walk(rel_path):
            umask_fix_perms(basedir, self.config.umask, 0o777, self.config.gid)
            for filename in files:
                path = os.path.join(basedir, filename)
                # Ignore symlinks
                if os.path.islink(path):
                    continue
                umask_fix_perms( path, self.config.umask, 0o666, self.config.gid )

    def _construct_path(self, obj, base_dir=None, dir_only=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False, **kwargs):
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
            # alt_name can contain parent directory references, but S3 will not
            # follow them, so if they are valid we normalize them out
            alt_name = os.path.normpath(alt_name)
        rel_path = os.path.join(*directory_hash_id(obj.id))
        if extra_dir is not None:
            if extra_dir_at_root:
                rel_path = os.path.join(extra_dir, rel_path)
            else:
                rel_path = os.path.join(rel_path, extra_dir)

        # for JOB_WORK directory
        if obj_dir:
            rel_path = os.path.join(rel_path, str(obj.id))
        if base_dir:
            base = self.extra_dirs.get(base_dir)
            return os.path.join(base, rel_path)

        # S3 folders are marked by having trailing '/' so add it now
        rel_path = '%s/' % rel_path

        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else "dataset_%s.dat" % obj.id)
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
        except S3ResponseError:
            log.exception("Could not get size of key '%s' from S3", rel_path)
            return -1

    def _key_exists(self, rel_path):
        exists = False
        try:
            # A hackish way of testing if the rel_path is a folder vs a file
            is_dir = rel_path[-1] == '/'
            if is_dir:
                keyresult = self.bucket.get_all_keys(prefix=rel_path)
                if len(keyresult) > 0:
                    exists = True
                else:
                    exists = False
            else:
                key = Key(self.bucket, rel_path)
                exists = key.exists()
        except S3ResponseError:
            log.exception("Trouble checking existence of S3 key '%s'", rel_path)
            return False
        if rel_path[0] == '/':
            raise
        return exists

    def _in_cache(self, rel_path):
        """ Check if the given dataset is in the local cache and return True if so. """
        # log.debug("------ Checking cache for rel_path %s" % rel_path)
        cache_path = self._get_cache_path(rel_path)
        return os.path.exists(cache_path)
        # TODO: Part of checking if a file is in cache should be to ensure the
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
        #     return False

    def _pull_into_cache(self, rel_path):
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir))
        # Now pull in the file
        file_ok = self._download(rel_path)
        self._fix_permissions(self._get_cache_path(rel_path_dir))
        return file_ok

    def _transfer_cb(self, complete, total):
        self.transfer_progress += 10

    def _download(self, rel_path):
        try:
            log.debug("Pulling key '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))
            key = self.bucket.get_key(rel_path)
            # Test if cache is large enough to hold the new file
            if self.cache_size > 0 and key.size > self.cache_size:
                log.critical("File %s is larger (%s) than the cache size (%s). Cannot download.",
                             rel_path, key.size, self.cache_size)
                return False
            if self.use_axel:
                log.debug("Parallel pulled key '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))
                ncores = multiprocessing.cpu_count()
                url = key.generate_url(7200)
                ret_code = subprocess.call("axel -a -n %s '%s'" % (ncores, url))
                if ret_code == 0:
                    return True
            else:
                log.debug("Pulled key '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))
                self.transfer_progress = 0  # Reset transfer progress counter
                key.get_contents_to_filename(self._get_cache_path(rel_path), cb=self._transfer_cb, num_cb=10)
                return True
        except S3ResponseError:
            log.exception("Problem downloading key '%s' from S3 bucket '%s'", rel_path, self.bucket.name)
        return False

    def _push_to_os(self, rel_path, source_file=None, from_string=None):
        """
        Push the file pointed to by ``rel_path`` to the object store naming the key
        ``rel_path``. If ``source_file`` is provided, push that file instead while
        still using ``rel_path`` as the key name.
        If ``from_string`` is provided, set contents of the file to the value of
        the string.
        """
        try:
            source_file = source_file if source_file else self._get_cache_path(rel_path)
            if os.path.exists(source_file):
                key = Key(self.bucket, rel_path)
                if os.path.getsize(source_file) == 0 and key.exists():
                    log.debug("Wanted to push file '%s' to S3 key '%s' but its size is 0; skipping.", source_file, rel_path)
                    return True
                if from_string:
                    key.set_contents_from_string(from_string, reduced_redundancy=self.use_rr)
                    log.debug("Pushed data from string '%s' to key '%s'", from_string, rel_path)
                else:
                    start_time = datetime.now()
                    log.debug("Pushing cache file '%s' of size %s bytes to key '%s'", source_file, os.path.getsize(source_file), rel_path)
                    mb_size = os.path.getsize(source_file) / 1e6
                    if mb_size < 10 or (not self.multipart):
                        self.transfer_progress = 0  # Reset transfer progress counter
                        key.set_contents_from_filename(source_file,
                                                       reduced_redundancy=self.use_rr,
                                                       cb=self._transfer_cb,
                                                       num_cb=10)
                    else:
                        multipart_upload(self.s3server, self.bucket, key.name, source_file, mb_size)
                    end_time = datetime.now()
                    log.debug("Pushed cache file '%s' to key '%s' (%s bytes transfered in %s sec)",
                              source_file, rel_path, os.path.getsize(source_file), end_time - start_time)
                return True
            else:
                log.error("Tried updating key '%s' from source file '%s', but source file does not exist.",
                          rel_path, source_file)
        except S3ResponseError:
            log.exception("Trouble pushing S3 key '%s' from file '%s'", rel_path, source_file)
        return False

    def file_ready(self, obj, **kwargs):
        """
        A helper method that checks if a file corresponding to a dataset is
        ready and available to be used. Return ``True`` if so, ``False`` otherwise.
        """
        rel_path = self._construct_path(obj, **kwargs)
        # Make sure the size in cache is available in its entirety
        if self._in_cache(rel_path):
            if os.path.getsize(self._get_cache_path(rel_path)) == self._get_size_in_s3(rel_path):
                return True
            log.debug("Waiting for dataset %s to transfer from OS: %s/%s", rel_path,
                      os.path.getsize(self._get_cache_path(rel_path)), self._get_size_in_s3(rel_path))
        return False

    def exists(self, obj, **kwargs):
        in_cache = in_s3 = False
        rel_path = self._construct_path(obj, **kwargs)

        # Check cache
        if self._in_cache(rel_path):
            in_cache = True
        # Check S3
        in_s3 = self._key_exists(rel_path)
        # log.debug("~~~~~~ File '%s' exists in cache: %s; in s3: %s" % (rel_path, in_cache, in_s3))
        # dir_only does not get synced so shortcut the decision
        dir_only = kwargs.get('dir_only', False)
        base_dir = kwargs.get('base_dir', None)
        if dir_only:
            if in_cache or in_s3:
                return True
            # for JOB_WORK directory
            elif base_dir:
                if not os.path.exists(rel_path):
                    os.makedirs(rel_path)
                return True
            else:
                return False

        # TODO: Sync should probably not be done here. Add this to an async upload stack?
        if in_cache and not in_s3:
            self._push_to_os(rel_path, source_file=self._get_cache_path(rel_path))
            return True
        elif in_s3:
            return True
        else:
            return False

    def create(self, obj, **kwargs):
        if not self.exists(obj, **kwargs):

            # Pull out locally used fields
            extra_dir = kwargs.get('extra_dir', None)
            extra_dir_at_root = kwargs.get('extra_dir_at_root', False)
            dir_only = kwargs.get('dir_only', False)
            alt_name = kwargs.get('alt_name', None)

            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(obj.id))

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
            # self._push_to_os(s3_dir, from_string='')
            # If instructed, create the dataset in cache & in S3
            if not dir_only:
                rel_path = os.path.join(rel_path, alt_name if alt_name else "dataset_%s.dat" % obj.id)
                open(os.path.join(self.staging_path, rel_path), 'w').close()
                self._push_to_os(rel_path, from_string='')

    def empty(self, obj, **kwargs):
        if self.exists(obj, **kwargs):
            return bool(self.size(obj, **kwargs) > 0)
        else:
            raise ObjectNotFound( 'objectstore.empty, object does not exist: %s, kwargs: %s'
                                  % ( str( obj ), str( kwargs ) ) )

    def size(self, obj, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        if self._in_cache(rel_path):
            try:
                return os.path.getsize(self._get_cache_path(rel_path))
            except OSError as ex:
                log.info("Could not get size of file '%s' in local cache, will try S3. Error: %s", rel_path, ex)
        elif self.exists(obj, **kwargs):
            return self._get_size_in_s3(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size", rel_path)
        return 0

    def delete(self, obj, entire_dir=False, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        extra_dir = kwargs.get('extra_dir', None)
        base_dir = kwargs.get('base_dir', None)
        dir_only = kwargs.get('dir_only', False)
        obj_dir = kwargs.get('obj_dir', False)
        try:
            # Remove temparory data in JOB_WORK directory
            if base_dir and dir_only and obj_dir:
                shutil.rmtree(os.path.abspath(rel_path))
                return True

            # For the case of extra_files, because we don't have a reference to
            # individual files/keys we need to remove the entire directory structure
            # with all the files in it. This is easy for the local file system,
            # but requires iterating through each individual key in S3 and deleing it.
            if entire_dir and extra_dir:
                shutil.rmtree(self._get_cache_path(rel_path))
                results = self.bucket.get_all_keys(prefix=rel_path)
                for key in results:
                    log.debug("Deleting key %s", key.name)
                    key.delete()
                return True
            else:
                # Delete from cache first
                os.unlink(self._get_cache_path(rel_path))
                # Delete from S3 as well
                if self._key_exists(rel_path):
                    key = Key(self.bucket, rel_path)
                    log.debug("Deleting key %s", key.name)
                    key.delete()
                    return True
        except S3ResponseError:
            log.exception("Could not delete key '%s' from S3", rel_path)
        except OSError:
            log.exception('%s delete error', self.get_filename(obj, **kwargs))
        return False

    def get_data(self, obj, start=0, count=-1, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        # Check cache first and get file if not there
        if not self._in_cache(rel_path):
            self._pull_into_cache(rel_path)
        # Read the file content from cache
        data_file = open(self._get_cache_path(rel_path), 'r')
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def get_filename(self, obj, **kwargs):
        base_dir = kwargs.get('base_dir', None)
        dir_only = kwargs.get('dir_only', False)
        obj_dir = kwargs.get('obj_dir', False)
        rel_path = self._construct_path(obj, **kwargs)

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
            return os.path.abspath(rel_path)

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
        elif self.exists(obj, **kwargs):
            if dir_only:  # Directories do not get pulled into cache
                return cache_path
            else:
                if self._pull_into_cache(rel_path):
                    return cache_path
        # For the case of retrieving a directory only, return the expected path
        # even if it does not exist.
        # if dir_only:
        #     return cache_path
        raise ObjectNotFound( 'objectstore.get_filename, no cache_path: %s, kwargs: %s'
                              % ( str( obj ), str( kwargs ) ) )
        # return cache_path # Until the upload tool does not explicitly create the dataset, return expected path

    def update_from_file(self, obj, file_name=None, create=False, **kwargs):
        if create:
            self.create(obj, **kwargs)
        if self.exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            # Chose whether to use the dataset file itself or an alternate file
            if file_name:
                source_file = os.path.abspath(file_name)
                # Copy into cache
                cache_file = self._get_cache_path(rel_path)
                try:
                    if source_file != cache_file:
                        # FIXME? Should this be a `move`?
                        shutil.copy2(source_file, cache_file)
                    self._fix_permissions(cache_file)
                except OSError:
                    log.exception("Trouble copying source file '%s' to cache '%s'", source_file, cache_file)
            else:
                source_file = self._get_cache_path(rel_path)
            # Update the file on S3
            self._push_to_os(rel_path, source_file)
        else:
            raise ObjectNotFound( 'objectstore.update_from_file, object does not exist: %s, kwargs: %s'
                                  % ( str( obj ), str( kwargs ) ) )

    def get_object_url(self, obj, **kwargs):
        if self.exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            try:
                key = Key(self.bucket, rel_path)
                return key.generate_url(expires_in=86400)  # 24hrs
            except S3ResponseError:
                log.exception("Trouble generating URL for dataset '%s'", rel_path)
        return None

    def get_store_usage_percent(self):
        return 0.0


class SwiftObjectStore(S3ObjectStore):
    """
    Object store that stores objects as items in a Swift bucket. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and Swift.
    """

    def _configure_connection(self):
        log.debug("Configuring Swift Connection")
        self.conn = boto.connect_s3(aws_access_key_id=self.access_key,
                                    aws_secret_access_key=self.secret_key,
                                    is_secure=self.is_secure,
                                    host=self.host,
                                    port=self.port,
                                    calling_format=boto.s3.connection.OrdinaryCallingFormat(),
                                    path=self.conn_path)
