# This work originally developed by Stavros Sachtouris <saxtouri@grnet.gr>
# as part of the effort committed GRNET S.A. (Greek Research and Technology
# Network) in the context of the OpenMinTeD project (openminted.eu)

import logging
from ..objectstore import ObjectStore
from kamaki.clients import astakos, pithos, utils, ClientError

log = logging.getLogger(__name__)


def parse_config_xml(config_xml):
    """Parse and validate config_xml, return dict for convenience
    :param config_xml: (xml.etree.ElementTree.Element) root of XML subtree
    :returns: (dict) according to syntax
    :raises: various XML parse errors
    """
    r = dict()
    try:
        # Extract single values first
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
                    raise KeyError(msg)
            optional = tuple((k, element.get(k)) for k in optional_attrs)
            r[tag] = dict(required + optional)
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

        log.info('Authenticate Synnefo account')
        self._authenticate()
        log.info('Initialize Pithos+ client')
        self._init_pithos()

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
