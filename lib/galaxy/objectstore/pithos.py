# This work originally developed by Stavros Sachtouris <saxtouri@grnet.gr>
# as part of the effort committed GRNET S.A. (Greek Research and Technology
# Network) in the context of the OpenMinTeD project (openminted.eu)

import logging
import os
import shutil

try:
    from kamaki.clients import (
        astakos,
        Client as KamakiClient,
        ClientError,
        pithos,
        utils
    )
except ImportError:
    KamakiClient = None

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound
)
from galaxy.util import (
    directory_hash_id,
    umask_fix_perms,
)
from galaxy.util.path import safe_relpath
from ..objectstore import ObjectStore

NO_KAMAKI_ERROR_MESSAGE = (
    "ObjectStore configured, but no kamaki.clients dependency available."
    "Please install and properly configure kamaki.clients or modify Object "
    "Store configuration.")

log = logging.getLogger(__name__)


def parse_config_xml(config_xml):
    """Parse and validate config_xml, return dict for convenience
    :param config_xml: (xml.etree.ElementTree.Element) root of XML subtree
    :returns: (dict) according to syntax
    :raises: various XML parse errors
    """
    r = dict()
    try:
        for tag, required_attrs, optional_attrs in (
                ('auth', ('url', 'token', ), ('ca_certs', 'ignore_ssl', )),
                ('container', ('name', ), ('project', )), ):
            element = config_xml.findall(tag)[0]
            required = tuple((k, element.get(k)) for k in required_attrs)
            for k, v in required:
                if not v:
                    msg = 'No value for {tag}:{k} in XML tree'.format(
                        tag=tag, k=k)
                    log.error(msg)
                    raise Exception(msg)
            optional = tuple((k, element.get(k)) for k in optional_attrs)
            r[tag] = dict(required + optional)

        # Extract extra_dir
        tag, attrs = 'extra_dir', ('type', 'path')
        extra_dirs = config_xml.findall(tag)
        if not extra_dirs:
            msg = 'No {tag} element in XML tree'.format(tag=tag)
            log.error(msg)
            raise Exception(msg)
        r['extra_dirs'] = [
            dict(((k, e.get(k)) for k in attrs)) for e in extra_dirs]
        if 'job_work' not in (d['type'] for d in r['extra_dirs']):
            msg = 'No value for {0}:type="job_work" in XML tree'.format(tag)
            log.error(msg)
            raise Exception(msg)
    except Exception:
        log.exception(
            "Malformed PithosObjectStore Configuration XML -- "
            "unable to continue")
        raise
    return r


class PithosObjectStore(ObjectStore):
    """
    Object store that stores objects as items in a Pithos+ container.
    Cache is ignored for the time being.
    """

    def __init__(self, config, config_xml):
        if KamakiClient is None:
            raise Exception(NO_KAMAKI_ERROR_MESSAGE)
        super(PithosObjectStore, self).__init__(config)
        self.staging_path = self.config.file_path
        self.transfer_progress = 0
        log.info('Parse config_xml for pithos object store')
        self.config_dict = parse_config_xml(config_xml)
        log.debug(self.config_dict)

        log.info('Authenticate Synnefo account')
        self._authenticate()
        log.info('Initialize Pithos+ client')
        self._init_pithos()

        log.info('Define extra_dirs')
        self.extra_dirs = dict(
            (e['type'], e['path']) for e in self.config_dict['extra_dirs'])

    def _authenticate(self):
        auth = self.config_dict['auth']
        url, token = auth['url'], auth['token']
        ca_certs = auth.get('ca_certs')
        if ca_certs:
            utils.https.patch_with_certs(ca_certs)
        elif auth.get('ignore_ssl').lower() in ('true', 'yes', 'on'):
            utils.https.patch_ignore_ssl()
        self.astakos = astakos.AstakosClient(url, token)

    def _init_pithos(self):
        uuid, token = self.astakos.user_term('id'), self.astakos.token
        service_type = pithos.PithosClient.service_type
        pithos_url = self.astakos.get_endpoint_url(service_type)
        container = self.config_dict['container']['name']
        self.pithos = pithos.PithosClient(pithos_url, token, uuid, container)

        # Create container if not exist, or reassign to named project
        project = self.config_dict['container'].get('project', None)
        try:
            c = self.pithos.get_container_info()
        except ClientError as ce:
            if ce.status not in (404, ):
                raise
            c = self.pithos.create_container(project_id=project)
            return
        if project and c.get('x-container-policy-project') != project:
            self.pithos.reassign_container(project)

    def _construct_path(
            self, obj,
            base_dir=None, dir_only=None, extra_dir=None,
            extra_dir_at_root=False, alt_name=None, obj_dir=False, **kwargs):
        """Construct path from object and parameters"""
        # param extra_dir: should never be constructed from provided data but
        # just make sure there are no shenannigans afoot
        if extra_dir and extra_dir != os.path.normpath(extra_dir):
            log.warning('extra_dir is not normalized: {0}'.format(extra_dir))
            raise ObjectInvalid("The requested object is invalid")
        # ensure that any parent directory references in alt_name would not
        # result in a path not contained in the directory path constructed here
        if alt_name:
            if not safe_relpath(alt_name):
                log.warning(
                    'alt_name would locate path outside dir: {0}'.format(
                        alt_name))
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

        # Pithos+ folders are marked by having trailing '/' so add it now
        rel_path = '{0}/'.format(rel_path)

        if not dir_only:
            an = alt_name if alt_name else 'dataset_{0}.dat'.format(obj.id)
            rel_path = os.path.join(rel_path, an)
        return rel_path

    def _get_cache_path(self, rel_path):
        return os.path.abspath(os.path.join(self.staging_path, rel_path))

    def _in_cache(self, rel_path):
        """Check if the given dataset is in the local cache and return True if
           so.
        """
        cache_path = self._get_cache_path(rel_path)
        return os.path.exists(cache_path)

    def _fix_permissions(self, rel_path):
        """ Set permissions on rel_path"""
        for basedir, _, files in os.walk(rel_path):
            umask_fix_perms(basedir, self.config.umask, 0o777, self.config.gid)
            for filename in files:
                path = os.path.join(basedir, filename)
                # Ignore symlinks
                if os.path.islink(path):
                    continue
                umask_fix_perms(
                    path, self.config.umask, 0o666, self.config.gid)

    def _pull_into_cache(self, rel_path):
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        rel_cache_path_dir = self._get_cache_path(rel_path_dir)
        if not os.path.exists(rel_cache_path_dir):
            os.makedirs(self._get_cache_path(rel_path_dir))
        # Now pull in the file
        cache_path = self._get_cache_path(rel_path_dir)
        self.pithos.download_object(rel_path, cache_path)
        self._fix_permissions(cache_path)
        return cache_path

    # No need to overwrite "shutdown"

    def exists(self, obj, **kwargs):
        """Check if file exists, fix if file in cache and not on Pithos+
        :returns: weather the file exists remotely or in cache
        """
        path = self._construct_path(obj, **kwargs)
        try:
            self.pithos.get_object_info(path)
            return True
        except ClientError as ce:
            if ce.status not in (404, ):
                raise

        in_cache = self._in_cache(path)
        dir_only = kwargs.get('dir_only', False)
        if dir_only:
            base_dir = kwargs.get('base_dir', None)
            if in_cache:
                return True
            elif base_dir:  # for JOB_WORK directory
                if not os.path.exists(path):
                    os.makedirs(path)
                return True
            return False

        if in_cache:
            cache_path = self._get_cache_path(path)
            # Maybe the upload should have happened in some thread elsewhere?
            with open(cache_path) as f:
                self.pithos.upload_object(path, f)
            return True
        return False

    def create(self, obj, **kwargs):
        """Touch a file (aka create empty), if it doesn't exist"""
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

            if dir_only:
                self.pithos.upload_from_string(
                    rel_path, '', content_type='application/directory')
            else:
                rel_path = os.path.join(
                    rel_path,
                    alt_name if alt_name else 'dataset_{0}.dat'.format(obj.id))
                new_file = os.path.join(self.staging_path, rel_path)
                open(new_file, 'w').close()
                self.pithos.upload_from_string(rel_path, '')

    def empty(self, obj, **kwargs):
        """
        :returns: weather the object has content
        :raises ObjectNotFound:
        """
        if not self.exists(obj, **kwargs):
            raise ObjectNotFound(
                'objectstore.empty, object does not exist: {obj}, '
                'kwargs: {kwargs}'.format(obj=obj, kwargs=kwargs))
        return bool(self.size(obj, **kwargs))

    def size(self, obj, **kwargs):
        """
        :returns: The size of the object, or 0 if it doesn't exist (sorry for
            that, not our fault, the ObjectStore interface is like that some
            times)
        """
        path = self._construct_path(obj, **kwargs)
        if self._in_cache(path):
            try:
                return os.path.getsize(self._get_cache_path(path))
            except OSError as ex:
                log.warning(
                    'Could not get size of file {path} in local cache,'
                    'will try Pithos. Error: {err}'.format(path=path, err=ex))
        try:
            file = self.pithos.get_object_info(path)
        except ClientError as ce:
            if ce.status not in (404, ):
                raise
            return 0
        return int(file['content-length'])

    def delete(self, obj, **kwargs):
        """Delete the object
        :returns: weather the object was deleted
        """
        path = self._construct_path(obj, **kwargs)
        base_dir = kwargs.get('base_dir', None)
        dir_only = kwargs.get('dir_only', False)
        obj_dir = kwargs.get('obj_dir', False)
        try:
            if all((base_dir, dir_only, obj_dir)):
                shutil.rmtree(os.path.abspath(path))
                return True
            cache_path = self._get_cache_path(path)

            entire_dir = kwargs.get('entire_dir', False)
            extra_dir = kwargs.get('extra_dir', False)
            if entire_dir and extra_dir:
                shutil.rmtree(cache_path)
                log.debug('On Pithos: delete -r {path}/'.format(path=path))
                self.pithos.del_object(path, delimiter='/')
                return True
            else:
                os.unlink(cache_path)
                self.pithos.del_object(path)
        except OSError:
            log.exception(
                '{0} delete error'.format(self.get_filename(obj, **kwargs)))
        except ClientError as ce:
            log.exception('Could not delete {path} from Pithos, {err}'.format(
                path=path, err=ce))
        return False

    def get_data(self, obj, start=0, count=-1, **kwargs):
        """Fetch (e.g., download) data
        :param start: Chunk of data starts here
        :param count: Fetch at most as many data, fetch all if negative
        """
        path = self._construct_path(obj, **kwargs)
        if self._in_cache(path):
            cache_path = self._pull_into_cache(path)
        else:
            cache_path = self._get_cache_path(path)
        data_file = open(cache_path, 'r')
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def get_filename(self, obj, **kwargs):
        """Get the expected filename with absolute path"""
        base_dir = kwargs.get('base_dir', None)
        dir_only = kwargs.get('dir_only', False)
        obj_dir = kwargs.get('obj_dir', False)
        path = self._construct_path(obj, **kwargs)

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
            return os.path.abspath(path)
        cache_path = self._get_cache_path(path)
        if dir_only:
            if not os.path.exists(cache_path):
                os.makedirs(cache_path)
            return cache_path
        if self._in_cache(path):
            return cache_path
        elif self.exists(obj, **kwargs):
            if not dir_only:
                self._pull_into_cache(path)
                return cache_path
        raise ObjectNotFound(
            'objectstore.get_filename, no cache_path: {obj}, '
            'kwargs: {kwargs}'.format(obj, kwargs))

    def update_from_file(self, obj, **kwargs):
        """Update the store when a file is updated"""
        if kwargs.get('create'):
            self.create(obj, **kwargs)
        if not self.exists(obj, **kwargs):
            raise ObjectNotFound(
                'objectstore.update_from_file, object does not exist: {obj}, '
                'kwargs: {kwargs}'.format(obj, kwargs))

        path = self._construct_path(obj, **kwargs)
        cache_path = self._get_cache_path(path)
        file_name = kwargs.get('file_name')
        if file_name:
            source_path = os.path.abspath(file_name)
            try:
                if source_path != cache_path:
                    shutil.copy2(source_path, cache_path)
                self._fix_permissions(cache_path)
            except OSError:
                log.exception(
                    'Trouble copying source file "{source}" to cache "{cache}"'
                    ''.format(source=source_path, cache=cache_path))
        else:
            with open(cache_path) as f:
                self.pithos.upload_object(obj, f)

    def get_object_url(self, obj, **kwargs):
        """
        :returns: URL for direct access, None if no object
        """
        if self.exists(obj, **kwargs):
            path = self._construct_path(obj, **kwargs)
            try:
                return self.pithos.publish_object(path)
            except ClientError as ce:
                log.exception(
                    'Trouble generating URL for dataset "{}"'.format(path))
                log.exception('Kamaki: {0}'.format(ce))
        return None

    def get_store_usage_percent(self):
        """
        :returns: percentage indicating how full the store is
        """
        quotas = self.astakos.get_quotas()
        project = self.config_dict['container']['project']
        pithos_quotas = quotas[project]['pithos.diskspace']
        usage = pithos_quotas['usage']
        limit = min(pithos_quotas['limit'], pithos_quotas['project_limit'])
        return (100.0 * usage) / limit
