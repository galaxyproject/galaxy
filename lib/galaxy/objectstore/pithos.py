# This work originally developed by Stavros Sachtouris <saxtouri@grnet.gr>
# as part of the effort committed GRNET S.A. (Greek Research and Technology
# Network) in the context of the OpenMinTeD project (openminted.eu)

import logging
from kamaki.clients import astakos, pithos, utils, ClientError
from galaxy.exceptions import ObjectInvalid
from galaxy.util import (
    directory_hash_id,
    safe_relpath,
)
from ..objectstore import ObjectStore

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

    def exists(self, obj, **kwargs):
        """
        :returns: weather the file exists remotely or in cache
        """
        # TODO: Check if file exists in cache
        path = self._construct_path(obj, **kwargs)
        try:
            self.pithos.get_object_info(path)
        except ClientError as ce:
            if ce.status not in (404, ):
                raise
            return False
        return True
