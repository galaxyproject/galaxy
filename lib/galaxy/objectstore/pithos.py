# This work originally developed by Stavros Sachtouris <saxtouri@grnet.gr>
# as part of the effort committed GRNET S.A. (Greek Research and Technology
# Network) in the context of the OpenMinTeD project (openminted.eu)

import logging
import os

try:
    from kamaki.clients import (
        astakos,
        Client as KamakiClient,
        ClientError,
        pithos,
        utils,
    )
except ImportError:
    KamakiClient = None

from galaxy.util import directory_hash_id
from ._caching_base import CachingConcreteObjectStore

NO_KAMAKI_ERROR_MESSAGE = (
    "ObjectStore configured, but no kamaki.clients dependency available."
    "Please install and properly configure kamaki.clients or modify Object "
    "Store configuration."
)

log = logging.getLogger(__name__)


def parse_config_xml(config_xml):
    """Parse and validate config_xml, return dict for convenience
    :param config_xml: (lxml.etree.Element) root of XML subtree
    :returns: (dict) according to syntax
    :raises: various XML parse errors
    """
    r = {}
    try:
        for tag, required_attrs, optional_attrs in (
            (
                "auth",
                (
                    "url",
                    "token",
                ),
                (
                    "ca_certs",
                    "ignore_ssl",
                ),
            ),
            ("container", ("name",), ("project",)),
        ):
            element = config_xml.findall(tag)[0]
            required = tuple((k, element.get(k)) for k in required_attrs)
            for k, v in required:
                if not v:
                    msg = f"No value for {tag}:{k} in XML tree"
                    log.error(msg)
                    raise Exception(msg)
            optional = tuple((k, element.get(k)) for k in optional_attrs)
            r[tag] = dict(required + optional)

        # Extract extra_dir
        tag, attrs = "extra_dir", ("type", "path")
        extra_dirs = config_xml.findall(tag)
        if not extra_dirs:
            msg = f"No {tag} element in XML tree"
            log.error(msg)
            raise Exception(msg)
        r["extra_dirs"] = [{k: e.get(k) for k in attrs} for e in extra_dirs]
        r["private"] = CachingConcreteObjectStore.parse_private_from_config_xml(config_xml)
        if "job_work" not in (d["type"] for d in r["extra_dirs"]):
            msg = f'No value for {tag}:type="job_work" in XML tree'
            log.error(msg)
            raise Exception(msg)
    except Exception:
        log.exception("Malformed PithosObjectStore Configuration XML, unable to continue")
        raise
    return r


class PithosObjectStore(CachingConcreteObjectStore):
    """
    Object store that stores objects as items in a Pithos+ container.
    Cache is ignored for the time being.
    """

    store_type = "pithos"

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)
        self.staging_path = self.config.file_path
        log.info("Parse config_xml for pithos object store")
        self.config_dict = config_dict

        self._initialize()

    def _initialize(self):
        if KamakiClient is None:
            raise Exception(NO_KAMAKI_ERROR_MESSAGE)

        self._ensure_staging_path_writable()
        log.info("Authenticate Synnefo account")
        self._authenticate()
        log.info("Initialize Pithos+ client")
        self._init_pithos()

    @classmethod
    def parse_xml(clazz, config_xml):
        return parse_config_xml(config_xml)

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(self.config_dict)
        return as_dict

    def _authenticate(self):
        auth = self.config_dict["auth"]
        url, token = auth["url"], auth["token"]
        ca_certs = auth.get("ca_certs")
        if ca_certs:
            utils.https.patch_with_certs(ca_certs)
        elif auth.get("ignore_ssl").lower() in ("true", "yes", "on"):
            utils.https.patch_ignore_ssl()
        self.astakos = astakos.AstakosClient(url, token)

    def _init_pithos(self):
        uuid, token = self.astakos.user_term("id"), self.astakos.token
        service_type = pithos.PithosClient.service_type
        pithos_url = self.astakos.get_endpoint_url(service_type)
        container = self.config_dict["container"]["name"]
        self.pithos = pithos.PithosClient(pithos_url, token, uuid, container)

        # Create container if not exist, or reassign to named project
        project = self.config_dict["container"].get("project", None)
        try:
            c = self.pithos.get_container_info()
        except ClientError as ce:
            if ce.status not in (404,):
                raise
            c = self.pithos.create_container(project_id=project)
            return
        if project and c.get("x-container-policy-project") != project:
            self.pithos.reassign_container(project)

    def _download(self, rel_path):
        local_destination = self._get_cache_path(rel_path)
        self.pithos.download_object(rel_path, local_destination)

    # No need to overwrite "shutdown"

    def _exists(self, obj, **kwargs) -> bool:
        """Check if file exists, fix if file in cache and not on Pithos+
        :returns: weather the file exists remotely or in cache
        """
        path = self._construct_path(obj, **kwargs)
        try:
            self.pithos.get_object_info(path)
            return True
        except ClientError as ce:
            if ce.status not in (404,):
                raise

        in_cache = self._in_cache(path)
        dir_only = kwargs.get("dir_only", False)
        if dir_only:
            base_dir = kwargs.get("base_dir", None)
            if in_cache:
                return True
            elif base_dir:  # for JOB_WORK directory
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                return True
            return False

        if in_cache:
            cache_path = self._get_cache_path(path)
            # Maybe the upload should have happened in some thread elsewhere?
            with open(cache_path) as f:
                self.pithos.upload_object(path, f)
            return True
        return False

    def _create(self, obj, **kwargs):
        """Touch a file (aka create empty), if it doesn't exist"""
        if not self._exists(obj, **kwargs):
            # Pull out locally used fields
            extra_dir = kwargs.get("extra_dir", None)
            extra_dir_at_root = kwargs.get("extra_dir_at_root", False)
            dir_only = kwargs.get("dir_only", False)
            alt_name = kwargs.get("alt_name", None)

            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(self._get_object_id(obj)))

            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)

            # Create given directory in cache
            cache_dir = os.path.join(self.staging_path, rel_path)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)

            if dir_only:
                self.pithos.upload_from_string(rel_path, "", content_type="application/directory")
            else:
                rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")
                new_file = os.path.join(self.staging_path, rel_path)
                open(new_file, "w").close()
                self.pithos.upload_from_string(rel_path, "")
        return self

    def _get_remote_size(self, path):
        try:
            file = self.pithos.get_object_info(path)
        except ClientError as ce:
            if ce.status not in (404,):
                raise
            return 0
        return int(file["content-length"])

    def _delete_remote_all(self, path: str) -> bool:
        try:
            log.debug(f"On Pithos: delete -r {path}/")
            self.pithos.del_object(path, delimiter="/")
            return True
        except ClientError:
            log.exception(f"Could not delete path '{path}' from Pithos")
            return False

    def _delete_existing_remote(self, path: str) -> bool:
        try:
            self.pithos.del_object(path)
            return True
        except ClientError:
            log.exception(f"Could not delete path '{path}' from Pithos")
            return False

    def _get_object_url(self, obj, **kwargs):
        """
        :returns: URL for direct access, None if no object
        """
        if self._exists(obj, **kwargs):
            path = self._construct_path(obj, **kwargs)
            try:
                return self.pithos.publish_object(path)
            except ClientError as ce:
                log.exception(f'Trouble generating URL for dataset "{path}"')
                log.exception(f"Kamaki: {ce}")
        return None

    def _get_store_usage_percent(self):
        """
        :returns: percentage indicating how full the store is
        """
        quotas = self.astakos.get_quotas()
        project = self.config_dict["container"]["project"]
        pithos_quotas = quotas[project]["pithos.diskspace"]
        usage = pithos_quotas["usage"]
        limit = min(pithos_quotas["limit"], pithos_quotas["project_limit"])
        return (100.0 * usage) / limit
