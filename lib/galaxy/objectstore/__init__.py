"""
objectstore package, abstraction for storing blobs of data for use in Galaxy.

all providers ensure that data can be accessed on the filesystem for running
tools
"""

import abc
import logging
import os
import random
import shutil
import threading
import time
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
)
from uuid import uuid4

import yaml
from pydantic import BaseModel
from typing_extensions import (
    Literal,
    Protocol,
)

from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    MalformedContents,
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.util import (
    asbool,
    directory_hash_id,
    force_symlink,
    in_directory,
    parse_xml,
    umask_fix_perms,
)
from galaxy.util.bunch import Bunch
from galaxy.util.path import (
    safe_makedirs,
    safe_relpath,
    safe_walk,
)
from galaxy.util.sleeper import Sleeper
from .badges import (
    BadgeDict,
    read_badges,
    serialize_badges,
    StoredBadgeDict,
)
from .caching import CacheTarget
from .templates import ObjectStoreConfiguration

if TYPE_CHECKING:
    from galaxy.model import (
        Dataset,
        DatasetInstance,
    )

NO_SESSION_ERROR_MESSAGE = (
    "Attempted to 'create' object store entity in configuration with no database session present."
)
DEFAULT_PRIVATE = False
DEFAULT_QUOTA_SOURCE = None  # Just track quota right on user object in Galaxy.
DEFAULT_QUOTA_ENABLED = True  # enable quota tracking in object stores by default
DEFAULT_DEVICE_ID = None
USER_OBJECTS_SCHEME = "user_objects://"

log = logging.getLogger(__name__)


def is_user_object_store(object_store_id: Optional[str]) -> bool:
    return object_store_id is not None and object_store_id.startswith(USER_OBJECTS_SCHEME)


class UserObjectStoreResolver(Protocol):
    def resolve_object_store_uri_config(self, uri: str) -> ObjectStoreConfiguration:
        pass

    def resolve_object_store_uri(self, uri: str) -> "ConcreteObjectStore":
        pass


class BaseUserObjectStoreResolver(UserObjectStoreResolver, metaclass=abc.ABCMeta):
    _app_config: "UserObjectStoresAppConfig"

    @abc.abstractmethod
    def resolve_object_store_uri_config(self, uri: str) -> ObjectStoreConfiguration:
        """Resolve the supplied object store URI into a concrete object store configuration."""
        pass

    def resolve_object_store_uri(self, uri: str) -> "ConcreteObjectStore":
        object_store_configuration = self.resolve_object_store_uri_config(uri)
        return concrete_object_store(object_store_configuration, self._app_config)


class ObjectStore(metaclass=abc.ABCMeta):
    """ObjectStore interface.

    FIELD DESCRIPTIONS (these apply to all the methods in this class):

    :type obj: StorableObject
    :param obj: A Galaxy object with an assigned database ID accessible via
        the .id attribute.

    :type base_dir: string
    :param base_dir: A key in `self.extra_dirs` corresponding to the base
        directory in which this object should be created, or `None` to specify
        the default directory.

    :type dir_only: boolean
    :param dir_only: If `True`, check only the path where the file identified
        by `obj` should be located, not the dataset itself. This option applies
        to `extra_dir` argument as well.

    :type extra_dir: string
    :param extra_dir: Append `extra_dir` to the directory structure where the
        dataset identified by `obj` should be located. (e.g.,
        000/extra_dir/obj.id). Valid values include 'job_work' (defaulting to
        config.jobs_directory =
        '$GALAXY_ROOT/database/jobs_directory');
        'temp' (defaulting to config.new_file_path =
        '$GALAXY_ROOT/database/tmp').

    :type extra_dir_at_root: boolean
    :param extra_dir_at_root: Applicable only if `extra_dir` is set. If True,
        the `extra_dir` argument is placed at root of the created directory
        structure rather than at the end (e.g., extra_dir/000/obj.id vs.
        000/extra_dir/obj.id)

    :type alt_name: string
    :param alt_name: Use this name as the alternative name for the created
        dataset rather than the default.

    :type obj_dir: boolean
    :param obj_dir: Append a subdirectory named with the object's ID (e.g.
        000/obj.id)
    """

    @abc.abstractmethod
    def exists(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """Return True if the object identified by `obj` exists, False otherwise."""
        raise NotImplementedError()

    @abc.abstractmethod
    def construct_path(
        self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None
    ):
        raise NotImplementedError()

    @abc.abstractmethod
    def create(
        self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False
    ):
        """
        Mark the object (`obj`) as existing in the store, but with no content.

        This method will create a proper directory structure for
        the file if the directory does not already exist.

        The method returns the concrete objectstore the supplied object is stored
        in.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def empty(self, obj, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Test if the object identified by `obj` has content.

        If the object does not exist raises `ObjectNotFound`.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def size(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False) -> int:
        """
        Return size of the object identified by `obj`.

        If the object does not exist, return 0.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(
        self,
        obj,
        entire_dir=False,
        base_dir=None,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
    ):
        """
        Delete the object identified by `obj`.

        :type entire_dir: boolean
        :param entire_dir: If True, delete the entire directory pointed to by
                           extra_dir. For safety reasons, this option applies
                           only for and in conjunction with the extra_dir or
                           obj_dir options.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_data(
        self,
        obj,
        start=0,
        count=-1,
        base_dir=None,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
    ):
        """
        Fetch `count` bytes of data offset by `start` bytes using `obj.id`.

        If the object does not exist raises `ObjectNotFound`.

        :type start: int
        :param start: Set the position to start reading the dataset file

        :type count: int
        :param count: Read at most `count` bytes from the dataset
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_filename(
        self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False
    ):
        """
        Get the expected filename with absolute path for object with id `obj.id`.

        This can be used to access the contents of the object.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def update_from_file(
        self,
        obj,
        base_dir=None,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
        file_name=None,
        create=False,
        preserve_symlinks=False,
    ):
        """
        Inform the store that the file associated with `obj.id` has been updated.

        If `file_name` is provided, update from that file instead of the
        default.
        If the object does not exist raises `ObjectNotFound`.

        :type file_name: string
        :param file_name: Use file pointed to by `file_name` as the source for
                          updating the dataset identified by `obj`

        :type create: boolean
        :param create: If True and the default dataset does not exist, create
            it first.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_object_url(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Return the URL for direct access if supported, otherwise return None.

        Note: need to be careful to not bypass dataset security with this.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_concrete_store_name(self, obj):
        """Return a display name or title of the objectstore corresponding to obj.

        To accommodate nested objectstores, obj is passed in so this metadata can
        be returned for the ConcreteObjectStore corresponding to the object.

        If the dataset is in a new or discarded state and an object_store_id has not
        yet been set, this may return ``None``.
        """

    @abc.abstractmethod
    def get_concrete_store_description_markdown(self, obj):
        """Return a longer description of how data 'obj' is stored.

        To accommodate nested objectstores, obj is passed in so this metadata can
        be returned for the ConcreteObjectStore corresponding to the object.

        If the dataset is in a new or discarded state and an object_store_id has not
        yet been set, this may return ``None``.
        """

    @abc.abstractmethod
    def get_concrete_store_badges(self, obj) -> List[BadgeDict]:
        """Return a list of dictified badges summarizing the object store configuration."""

    @abc.abstractmethod
    def is_private(self, obj):
        """Return True iff supplied object is stored in private ConcreteObjectStore."""

    def object_store_ids(self, private=None):
        """Return IDs of all concrete object stores - either private ones or non-private ones.

        This should just return an empty list for non-DistributedObjectStore object stores,
        i.e. concrete objectstores and the HierarchicalObjectStore since these do not
        use the object_store_id column for objects (Galaxy Datasets).
        """
        return []

    def object_store_allows_id_selection(self) -> bool:
        """Return True if this object store respects object_store_id and allow selection of this."""
        return False

    def validate_selected_object_store_id(self, user, object_store_id: Optional[str]) -> Optional[str]:
        if object_store_id and not self.object_store_allows_id_selection():
            return "The current configuration doesn't allow selecting preferred object stores."
        return None

    def object_store_ids_allowing_selection(self) -> List[str]:
        """Return a non-emtpy list of allowed selectable object store IDs during creation."""
        return []

    def get_concrete_store_by_object_store_id(self, object_store_id: str) -> Optional["ConcreteObjectStore"]:
        """If this is a distributed object store, get ConcreteObjectStore by object_store_id."""
        return None

    @abc.abstractmethod
    def get_store_usage_percent(self):
        """Return the percentage indicating how full the store is."""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_store_by(self, obj):
        """Return how object is stored (by 'uuid', 'id', or None if not yet saved).

        Certain Galaxy remote data features aren't available if objects are stored by 'id'.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def cache_targets(self) -> List[CacheTarget]:
        """Return a list of CacheTargets used by this object store."""
        raise NotImplementedError()

    @abc.abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_quota_source_map(self):
        """Return QuotaSourceMap describing mapping of object store IDs to quota sources."""

    @abc.abstractmethod
    def get_device_source_map(self) -> "DeviceSourceMap":
        """Return DeviceSourceMap describing mapping of object store IDs to device sources."""


class BaseObjectStore(ObjectStore):
    store_by: str
    store_type: str

    def __init__(self, config, config_dict=None, **kwargs):
        """
        :type config: object
        :param config: An object, most likely populated from
            `galaxy/config.ini`, having the following attributes:

            * object_store_check_old_style (only used by the
              :class:`DiskObjectStore` subclass)
            * jobs_directory -- Each job is given a unique empty directory
              as its current working directory. This option defines in what
              parent directory those directories will be created.
            * new_file_path -- Used to set the 'temp' extra_dir.
        """
        if config_dict is None:
            config_dict = {}
        self.running = True
        self.config = config
        self.check_old_style = config.object_store_check_old_style
        self.galaxy_enable_quotas = config.enable_quotas
        extra_dirs = {}
        extra_dirs["job_work"] = config.jobs_directory
        extra_dirs["temp"] = config.new_file_path
        extra_dirs.update({e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])})
        self.extra_dirs = extra_dirs

    def start(self):
        """
        Call all postfork function(s) here. These functions spawn a thread.
        We register start(self) with app, so app starts the threads. Override
        this function in subclasses, as needed.
        """

    def shutdown(self):
        """Close any connections for this ObjectStore."""
        self.running = False

    @classmethod
    def parse_xml(clazz, config_xml):
        """Parse an XML description of a configuration for this object store.

        Return a configuration dictionary (such as would correspond to the YAML configuration)
        for the object store.
        """
        raise NotImplementedError()

    @classmethod
    def from_xml(clazz, config, config_xml, **kwd):
        config_dict = clazz.parse_xml(config_xml)
        return clazz(config, config_dict, **kwd)

    def to_dict(self):
        extra_dirs = []
        for extra_dir_type, extra_dir_path in self.extra_dirs.items():
            extra_dirs.append({"type": extra_dir_type, "path": extra_dir_path})
        store_type = self.store_type
        return {
            "config": config_to_dict(self.config),
            "extra_dirs": extra_dirs,
            "type": store_type,
        }

    def _get_object_id(self, obj):
        if hasattr(obj, self.store_by):
            obj_id = getattr(obj, self.store_by)
            if obj_id is None:
                obj.flush()
                return obj.id
            return obj_id
        else:
            # job's don't have uuids, so always use ID in this case when creating
            # job working directories.
            return obj.id

    def _invoke(self, delegate, obj=None, **kwargs):
        return self.__getattribute__(f"_{delegate}")(obj=obj, **kwargs)

    def exists(self, obj, **kwargs):
        return self._invoke("exists", obj, **kwargs)

    def construct_path(self, obj, **kwargs):
        return self._invoke("construct_path", obj, **kwargs)

    def create(self, obj, **kwargs):
        return self._invoke("create", obj, **kwargs)

    def empty(self, obj, **kwargs):
        return self._invoke("empty", obj, **kwargs)

    def size(self, obj, **kwargs):
        return self._invoke("size", obj, **kwargs)

    def delete(self, obj, **kwargs):
        return self._invoke("delete", obj, **kwargs)

    def get_data(self, obj, **kwargs):
        return self._invoke("get_data", obj, **kwargs)

    def get_filename(self, obj, **kwargs):
        return self._invoke("get_filename", obj, **kwargs)

    def update_from_file(self, obj, **kwargs):
        return self._invoke("update_from_file", obj, **kwargs)

    def get_object_url(self, obj, **kwargs):
        return self._invoke("get_object_url", obj, **kwargs)

    def get_concrete_store_name(self, obj):
        return self._invoke("get_concrete_store_name", obj)

    def get_concrete_store_description_markdown(self, obj):
        return self._invoke("get_concrete_store_description_markdown", obj)

    def get_concrete_store_badges(self, obj) -> List[BadgeDict]:
        return self._invoke("get_concrete_store_badges", obj)

    def get_store_usage_percent(self):
        return self._invoke("get_store_usage_percent")

    def get_store_by(self, obj, **kwargs):
        return self._invoke("get_store_by", obj, **kwargs)

    def is_private(self, obj):
        return self._invoke("is_private", obj)

    def cache_targets(self) -> List[CacheTarget]:
        return []

    @classmethod
    def parse_private_from_config_xml(clazz, config_xml):
        private = DEFAULT_PRIVATE
        if config_xml is not None:
            private = asbool(config_xml.attrib.get("private", DEFAULT_PRIVATE))
        return private

    @classmethod
    def parse_badges_from_config_xml(clazz, badges_xml):
        badges = []
        for e in badges_xml:
            type = e.tag
            message = e.text
            badges.append({"type": type, "message": message})
        return badges

    def get_quota_source_map(self):
        # I'd rather keep this abstract... but register_singleton wants it to be instantiable...
        raise NotImplementedError()

    def get_device_source_map(self):
        return DeviceSourceMap()


class ConcreteObjectStore(BaseObjectStore):
    """Subclass of ObjectStore for stores that don't delegate (non-nested).

    Adds store_by and quota_source functionality. These attributes do not make
    sense for the delegating object stores, they should describe files at actually
    persisted, not how a file is routed to a persistence source.
    """

    badges: List[StoredBadgeDict]
    device_id: Optional[str] = None
    cloud: bool = False

    def __init__(self, config, config_dict=None, **kwargs):
        """
        :type config: object
        :param config: An object, most likely populated from
            `galaxy/config.ini`, having the following attributes:

            * object_store_check_old_style (only used by the
              :class:`DiskObjectStore` subclass)
            * jobs_directory -- Each job is given a unique empty directory
              as its current working directory. This option defines in what
              parent directory those directories will be created.
            * new_file_path -- Used to set the 'temp' extra_dir.
        """
        if config_dict is None:
            config_dict = {}
        super().__init__(config=config, config_dict=config_dict, **kwargs)
        self.store_by = config_dict.get("store_by", None) or getattr(config, "object_store_store_by", "id")
        self.name = config_dict.get("name", None)
        self.description = config_dict.get("description", None)
        # Annotate this as true to prevent sharing of data.
        self.private = config_dict.get("private", DEFAULT_PRIVATE)
        # short label describing the quota source or null to use default
        # quota source right on user object.
        quota_config = config_dict.get("quota", {})
        self.quota_source = quota_config.get("source", DEFAULT_QUOTA_SOURCE)
        self.quota_enabled = quota_config.get("enabled", DEFAULT_QUOTA_ENABLED)
        self.device_id = config_dict.get("device", None)
        self.badges = read_badges(config_dict)

    def to_dict(self):
        rval = super().to_dict()
        rval["private"] = self.private
        rval["store_by"] = self.store_by
        rval["name"] = self.name
        rval["description"] = self.description
        rval["quota"] = {
            "source": self.quota_source,
            "enabled": self.quota_enabled,
        }
        rval["badges"] = self._get_concrete_store_badges(None)
        rval["device"] = self.device_id
        return rval

    def to_model(self, object_store_id: str) -> "ConcreteObjectStoreModel":
        return ConcreteObjectStoreModel(
            object_store_id=object_store_id,
            private=self.private,
            name=self.name,
            description=self.description,
            quota=QuotaModel(source=self.quota_source, enabled=self.quota_enabled),
            badges=self._get_concrete_store_badges(None),
            device=self.device_id,
        )

    def _get_concrete_store_badges(self, obj) -> List[BadgeDict]:
        return serialize_badges(
            self.badges,
            self.galaxy_enable_quotas and self.quota_enabled,
            self.private,
            False,
            self.cloud,
        )

    def _get_concrete_store_name(self, obj):
        return self.name

    def _get_concrete_store_description_markdown(self, obj):
        return self.description

    def _get_store_by(self, obj):
        return self.store_by

    def _is_private(self, obj):
        return self.private

    @property
    def cache_target(self) -> Optional[CacheTarget]:
        return None

    def cache_targets(self) -> List[CacheTarget]:
        cache_target = self.cache_target
        return [cache_target] if cache_target is not None else []

    def get_quota_source_map(self):
        quota_source_map = QuotaSourceMap(
            self.quota_source,
            self.quota_enabled,
        )
        return quota_source_map

    def get_device_source_map(self) -> "DeviceSourceMap":
        return DeviceSourceMap(self.device_id)


class DiskObjectStore(ConcreteObjectStore):
    """
    Standard Galaxy object store.

    Stores objects in files under a specific directory on disk.

    >>> from galaxy.util.bunch import Bunch
    >>> import tempfile
    >>> file_path=tempfile.mkdtemp()
    >>> obj = Bunch(id=1)
    >>> s = DiskObjectStore(Bunch(umask=0o077, jobs_directory=file_path, new_file_path=file_path, object_store_check_old_style=False, enable_quotas=True), dict(files_dir=file_path))
    >>> o = s.create(obj)
    >>> s.exists(obj)
    True
    >>> assert s.get_filename(obj) == file_path + '/000/dataset_1.dat'
    """

    store_type = "disk"

    def __init__(self, config, config_dict):
        """
        :type config: object
        :param config: An object, most likely populated from
            `galaxy/config.ini`, having the same attributes needed by
            :class:`ObjectStore` plus:

            * file_path -- Default directory to store objects to disk in.
            * umask -- the permission bits for newly created files.

        :type file_path: str
        :param file_path: Override for the `config.file_path` value.

        :type extra_dirs: dict
        :param extra_dirs: Keys are string, values are directory paths.
        """
        super().__init__(config, config_dict)
        self.file_path = os.path.abspath(config_dict.get("files_dir") or config.file_path)

    @classmethod
    def parse_xml(clazz, config_xml):
        extra_dirs = []
        config_dict = {}
        if config_xml is not None:
            store_by = config_xml.attrib.get("store_by", None)
            if store_by is not None:
                config_dict["store_by"] = store_by
            name = config_xml.attrib.get("name", None)
            if name is not None:
                config_dict["name"] = name
            device = config_xml.attrib.get("device", None)
            config_dict["device"] = device
            for e in config_xml:
                if e.tag == "quota":
                    config_dict["quota"] = {
                        "source": e.get("source", DEFAULT_QUOTA_SOURCE),
                        "enabled": asbool(e.get("enabled", DEFAULT_QUOTA_ENABLED)),
                    }
                elif e.tag == "files_dir":
                    config_dict["files_dir"] = e.get("path")
                elif e.tag == "description":
                    config_dict["description"] = e.text
                elif e.tag == "badges":
                    config_dict["badges"] = BaseObjectStore.parse_badges_from_config_xml(e)
                else:
                    extra_dirs.append({"type": e.get("type"), "path": e.get("path")})

        config_dict["extra_dirs"] = extra_dirs
        config_dict["private"] = BaseObjectStore.parse_private_from_config_xml(config_xml)
        return config_dict

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict["files_dir"] = self.file_path
        return as_dict

    def __get_filename(
        self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False
    ):
        """
        Return the absolute path for the file corresponding to the `obj.id`.

        This is regardless of whether or not the file exists.
        """
        path = self._construct_path(
            obj,
            base_dir=base_dir,
            dir_only=dir_only,
            extra_dir=extra_dir,
            extra_dir_at_root=extra_dir_at_root,
            alt_name=alt_name,
            obj_dir=False,
            old_style=True,
        )
        # For backward compatibility: check the old style root path first;
        # otherwise construct hashed path.
        if not os.path.exists(path):
            return self._construct_path(
                obj,
                base_dir=base_dir,
                dir_only=dir_only,
                extra_dir=extra_dir,
                extra_dir_at_root=extra_dir_at_root,
                alt_name=alt_name,
            )

    # TODO: rename to _disk_path or something like that to avoid conflicts with
    # children that'll use the local_extra_dirs decorator, e.g. S3
    def _construct_path(
        self,
        obj,
        old_style=False,
        base_dir=None,
        dir_only=False,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
        **kwargs,
    ):
        """
        Construct the absolute path for accessing the object identified by `obj.id`.

        :type base_dir: string
        :param base_dir: A key in self.extra_dirs corresponding to the base
                         directory in which this object should be created, or
                         None to specify the default directory.

        :type dir_only: boolean
        :param dir_only: If True, check only the path where the file
                         identified by `obj` should be located, not the
                         dataset itself. This option applies to `extra_dir`
                         argument as well.

        :type extra_dir: string
        :param extra_dir: Append the value of this parameter to the expected
            path used to access the object identified by `obj` (e.g.,
            /files/000/<extra_dir>/dataset_10.dat).

        :type alt_name: string
        :param alt_name: Use this name as the alternative name for the returned
                         dataset rather than the default.

        :type old_style: boolean
        param old_style: This option is used for backward compatibility. If
            `True` then the composed directory structure does not include a
            hash id (e.g., /files/dataset_10.dat (old) vs.
            /files/000/dataset_10.dat (new))
        """
        base = os.path.abspath(self.extra_dirs.get(base_dir) or self.file_path)
        # extra_dir should never be constructed from provided data but just
        # make sure there are no shenannigans afoot
        if extra_dir and extra_dir != os.path.normpath(extra_dir):
            log.warning("extra_dir is not normalized: %s", extra_dir)
            raise ObjectInvalid("The requested object is invalid")
        # ensure that any parent directory references in alt_name would not
        # result in a path not contained in the directory path constructed here
        if alt_name and not safe_relpath(alt_name):
            log.warning("alt_name would locate path outside dir: %s", alt_name)
            raise ObjectInvalid("The requested object is invalid")
        obj_id = self._get_object_id(obj)
        if old_style:
            if extra_dir is not None:
                path = os.path.join(base, extra_dir)
            else:
                path = base
        else:
            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(obj_id))
            # Create a subdirectory for the object ID
            if obj_dir:
                rel_path = os.path.join(rel_path, str(obj_id))
            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)
            path = os.path.join(base, rel_path)
        if not dir_only:
            assert (
                obj_id is not None
            ), f"The effective dataset identifier consumed by object store [{self.store_by}] must be set before a path can be constructed."
            path = os.path.join(path, alt_name if alt_name else f"dataset_{obj_id}.dat")
        return os.path.abspath(path)

    def _exists(self, obj, **kwargs):
        """Override `ObjectStore`'s stub and check on disk."""
        if self.check_old_style:
            path = self._construct_path(obj, old_style=True, **kwargs)
            # For backward compatibility: check root path first; otherwise
            # construct and check hashed path.
            if os.path.exists(path):
                return True
        path = self._construct_path(obj, **kwargs)
        return os.path.exists(path)

    def _create(self, obj, **kwargs):
        """Override `ObjectStore`'s stub by creating any files and folders on disk."""
        if not self._exists(obj, **kwargs):
            path = self._construct_path(obj, **kwargs)
            dir_only = kwargs.get("dir_only", False)
            # Create directory if it does not exist
            dir = path if dir_only else os.path.dirname(path)
            safe_makedirs(dir)
            # Create the file if it does not exist
            if not dir_only:
                open(path, "w").close()  # Should be rb?
                umask_fix_perms(path, self.config.umask, 0o666)
        return self

    def _empty(self, obj, **kwargs):
        """Override `ObjectStore`'s stub by checking file size on disk."""
        return self.size(obj, **kwargs) == 0

    def _size(self, obj, **kwargs) -> int:
        """Override `ObjectStore`'s stub by return file size on disk.

        Returns 0 if the object doesn't exist yet or other error.
        """
        if self._exists(obj, **kwargs):
            try:
                filepath = self._get_filename(obj, **kwargs)
                for _ in range(0, 2):
                    size = os.path.getsize(filepath)
                    if size != 0:
                        break
                    # May be legitimately 0, or there may be an issue with the FS / kernel, so we try again
                    time.sleep(0.01)
                return size
            except OSError:
                return 0
        else:
            return 0

    def _delete(self, obj, entire_dir=False, **kwargs):
        """Override `ObjectStore`'s stub; delete the file or folder on disk."""
        path = self._get_filename(obj, **kwargs)
        extra_dir = kwargs.get("extra_dir", None)
        obj_dir = kwargs.get("obj_dir", False)
        try:
            if entire_dir and (extra_dir or obj_dir):
                shutil.rmtree(path)
                return True
            os.remove(path)
            return True
        except FileNotFoundError:
            # Absolutely possible that a delete request races, but that's "fine".
            return True
        except OSError as ex:
            # Likely a race condition in which we delete the job working directory
            # and another process writes files into that directory.
            # If the path doesn't exist anymore, another rmtree call was successful.
            path = self.__get_filename(obj, **kwargs)
            if path is None:
                return True
            else:
                log.critical(f"{path} delete error {ex}", exc_info=True)
        return False

    def _get_data(self, obj, start=0, count=-1, **kwargs):
        """Override `ObjectStore`'s stub; retrieve data directly from disk."""
        data_file = open(self._get_filename(obj, **kwargs))  # Should be rb?
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def _get_filename(self, obj, **kwargs):
        """
        Override `ObjectStore`'s stub.

        If `object_store_check_old_style` is set to `True` in config then the
        root path is checked first.
        """
        if self.check_old_style:
            path = self._construct_path(obj, old_style=True, **kwargs)
            # For backward compatibility, check root path first; otherwise,
            # construct and return hashed path
            if os.path.exists(path):
                return path
        path = self._construct_path(obj, **kwargs)
        if not os.path.exists(path):
            raise ObjectNotFound
        return path

    def _update_from_file(self, obj, file_name=None, create=False, **kwargs):
        """`create` parameter is not used in this implementation."""
        preserve_symlinks = kwargs.pop("preserve_symlinks", False)
        # FIXME: symlinks and the object store model may not play well together
        # these should be handled better, e.g. registering the symlink'd file
        # as an object
        if create:
            self._create(obj, **kwargs)
        if file_name and self._exists(obj, **kwargs):
            try:
                if preserve_symlinks and os.path.islink(file_name):
                    force_symlink(os.readlink(file_name), self._get_filename(obj, **kwargs))
                else:
                    path = self._get_filename(obj, **kwargs)
                    shutil.copy(file_name, path)
                    umask_fix_perms(path, self.config.umask, 0o666)
            except shutil.SameFileError:
                # That's ok, we need to ignore this so that remote object stores can update
                # the remote object from the cache file path
                pass
            except OSError as ex:
                log.critical(f"Error copying {file_name} to {self.__get_filename(obj, **kwargs)}: {ex}")
                raise ex

    def _get_object_url(self, obj, **kwargs):
        """
        Override `ObjectStore`'s stub.

        Returns `None`, we have no URLs.
        """
        return None

    def _get_store_usage_percent(self, **kwargs):
        """Override `ObjectStore`'s stub by return percent storage used."""
        st = os.statvfs(self.file_path)
        return (float(st.f_blocks - st.f_bavail) / st.f_blocks) * 100


class NestedObjectStore(BaseObjectStore):
    """
    Base for ObjectStores that use other ObjectStores.

    Example: DistributedObjectStore, HierarchicalObjectStore
    """

    def __init__(self, config, config_xml=None):
        """Extend `ObjectStore`'s constructor."""
        super().__init__(config)
        self.backends = {}

    def shutdown(self):
        """For each backend, shuts them down."""
        for store in self.backends.values():
            store.shutdown()
        super().shutdown()

    def _exists(self, obj, **kwargs):
        """Determine if the `obj` exists in any of the backends."""
        return self._call_method("_exists", obj, False, False, **kwargs)

    def _create(self, obj, **kwargs):
        """Create a backing file in a random backend."""
        objectstore = random.choice(list(self.backends.values()))
        return objectstore.create(obj, **kwargs)

    def cache_targets(self) -> List[CacheTarget]:
        cache_targets = []
        for backend in self.backends.values():
            cache_targets.extend(backend.cache_targets())
        # TODO: merge more intelligently - de-duplicate paths and handle conflicting sizes/percents
        return cache_targets

    def _empty(self, obj, **kwargs):
        """For the first backend that has this `obj`, determine if it is empty."""
        return self._call_method("_empty", obj, True, False, **kwargs)

    def _size(self, obj, **kwargs):
        """For the first backend that has this `obj`, return its size."""
        return self._call_method("_size", obj, 0, False, **kwargs)

    def _delete(self, obj, **kwargs):
        """For the first backend that has this `obj`, delete it."""
        return self._call_method("_delete", obj, False, False, **kwargs)

    def _get_data(self, obj, **kwargs):
        """For the first backend that has this `obj`, get data from it."""
        return self._call_method("_get_data", obj, ObjectNotFound, True, **kwargs)

    def _get_filename(self, obj, **kwargs):
        """For the first backend that has this `obj`, get its filename."""
        return self._call_method("_get_filename", obj, ObjectNotFound, True, **kwargs)

    def _update_from_file(self, obj, **kwargs):
        """For the first backend that has this `obj`, update it from the given file."""
        if kwargs.get("create", False):
            self._create(obj, **kwargs)
            kwargs["create"] = False
        return self._call_method("_update_from_file", obj, ObjectNotFound, True, **kwargs)

    def _get_object_url(self, obj, **kwargs):
        """For the first backend that has this `obj`, get its URL."""
        return self._call_method("_get_object_url", obj, None, False, **kwargs)

    def _get_concrete_store_name(self, obj):
        return self._call_method("_get_concrete_store_name", obj, None, False)

    def _get_concrete_store_description_markdown(self, obj):
        return self._call_method("_get_concrete_store_description_markdown", obj, None, False)

    def _get_concrete_store_badges(self, obj) -> List[BadgeDict]:
        return self._call_method("_get_concrete_store_badges", obj, [], False)

    def _is_private(self, obj):
        return self._call_method("_is_private", obj, False, False)

    def _get_store_by(self, obj):
        return self._call_method("_get_store_by", obj, None, False)

    def _repr_object_for_exception(self, obj):
        try:
            # there are a few objects in python that don't have __class__
            obj_id = self._get_object_id(obj)
            return f"{obj.__class__.__name__}({self.store_by}={obj_id})"
        except AttributeError:
            return str(obj)

    def _call_method(self, method, obj, default, default_is_exception, **kwargs):
        """Check all children object stores for the first one with the dataset."""
        for store in self.backends.values():
            if store.exists(obj, **kwargs):
                return store.__getattribute__(method)(obj, **kwargs)
        if default_is_exception:
            raise default(
                f"objectstore, _call_method failed: {method} on {self._repr_object_for_exception(obj)}, kwargs: {kwargs}"
            )
        else:
            return default


def user_object_store_configuration_to_config_dict(object_store_config: ObjectStoreConfiguration, id) -> Dict[str, Any]:
    # convert a pydantic model describing a user object store into a config dict ready to be
    # slotted into a distributed job runner or stand alone.
    dynamic_object_store_as_dict = object_store_config.model_dump()
    dynamic_object_store_as_dict["id"] = id
    dynamic_object_store_as_dict["weight"] = 0
    # these are all forward facing object stores...
    dynamic_object_store_as_dict["store_by"] = "uuid"
    return dynamic_object_store_as_dict


class DistributedObjectStore(NestedObjectStore):
    """
    ObjectStore that defers to a list of backends.

    When getting objects the first store where the object exists is used.
    When creating objects they are created in a store selected randomly, but
    with weighting.
    """

    store_type = "distributed"
    _quota_source_map: Optional["QuotaSourceMap"]
    _device_source_map: Optional["DeviceSourceMap"]

    def __init__(
        self, config, config_dict, fsmon=False, user_object_store_resolver: Optional[UserObjectStoreResolver] = None
    ):
        """
        :type config: object
        :param config: An object, most likely populated from
            `galaxy/config.ini`, having the same attributes needed by
            :class:`NestedObjectStore` plus:

            * distributed_object_store_config_file

        :type config_xml: ElementTree

        :type fsmon: bool
        :param fsmon: If True, monitor the file system for free space,
            removing backends when they get too full.
        """
        super().__init__(config, config_dict)
        self._quota_source_map = None
        self._device_source_map = None
        self.backends = {}
        self.weighted_backend_ids = []
        self.original_weighted_backend_ids = []
        self.max_percent_full = {}
        self.global_max_percent_full = config_dict.get("global_max_percent_full", 0)
        self.search_for_missing = config_dict.get("search_for_missing", True)
        random.seed()

        user_selection_allowed = []
        for backend_def in config_dict["backends"]:
            backened_id = backend_def["id"]
            maxpctfull = backend_def.get("max_percent_full", 0)
            weight = backend_def["weight"]
            allow_selection = backend_def.get("allow_selection")
            if allow_selection:
                user_selection_allowed.append(backened_id)
            backend = build_object_store_from_config(config, config_dict=backend_def, fsmon=fsmon)

            self.backends[backened_id] = backend
            self.max_percent_full[backened_id] = maxpctfull

            for _ in range(0, weight):
                # The simplest way to do weighting: add backend ids to a
                # sequence the number of times equalling weight, then randomly
                # choose a backend from that sequence at creation
                self.weighted_backend_ids.append(backened_id)

        self.original_weighted_backend_ids = self.weighted_backend_ids
        self.user_object_store_resolver = user_object_store_resolver
        self.user_selection_allowed = user_selection_allowed
        self.allow_user_selection = bool(user_selection_allowed) or (user_object_store_resolver is not None)
        self.sleeper = None
        if fsmon and (self.global_max_percent_full or [_ for _ in self.max_percent_full.values() if _ != 0.0]):
            self.sleeper = Sleeper()
            self.filesystem_monitor_thread = threading.Thread(target=self.__filesystem_monitor, args=[self.sleeper])
            self.filesystem_monitor_thread.daemon = True
            self.filesystem_monitor_thread.start()
            log.info("Filesystem space monitor started")

    @classmethod
    def parse_xml(clazz, config_xml, legacy=False):
        if legacy:
            backends_root = config_xml
        else:
            backends_root = config_xml.find("backends")

        backends: List[Dict[str, Any]] = []
        config_dict = {
            "search_for_missing": asbool(backends_root.get("search_for_missing", True)),
            "global_max_percent_full": float(backends_root.get("maxpctfull", 0)),
            "backends": backends,
        }

        for b in [e for e in backends_root if e.tag == "backend"]:
            store_id = b.get("id")
            store_weight = int(b.get("weight", 1))
            store_maxpctfull = float(b.get("maxpctfull", 0))
            store_type = b.get("type", "disk")
            store_by = b.get("store_by", None)
            allow_selection = asbool(b.get("allow_selection"))

            objectstore_class, _ = type_to_object_store_class(store_type)
            backend_config_dict = objectstore_class.parse_xml(b)
            backend_config_dict["id"] = store_id
            backend_config_dict["weight"] = store_weight
            backend_config_dict["max_percent_full"] = store_maxpctfull
            backend_config_dict["type"] = store_type
            backend_config_dict["allow_selection"] = allow_selection
            if store_by is not None:
                backend_config_dict["store_by"] = store_by
            backends.append(backend_config_dict)

        return config_dict

    @classmethod
    def from_xml(
        clazz,
        config,
        config_xml,
        fsmon=False,
        user_object_store_resolver: Optional[UserObjectStoreResolver] = None,
        **kwd,
    ):
        legacy = False
        if config_xml is None:
            distributed_config = config.distributed_object_store_config_file
            assert distributed_config is not None, (
                "distributed object store ('object_store = distributed') "
                "requires a config file, please set one in "
                "'distributed_object_store_config_file')"
            )

            log.debug("Loading backends for distributed object store from %s", distributed_config)
            config_xml = parse_xml(distributed_config).getroot()
            legacy = True
        else:
            log.debug("Loading backends for distributed object store from %s", config_xml.get("id"))

        config_dict = clazz.parse_xml(config_xml, legacy=legacy)
        return clazz(config, config_dict, fsmon=fsmon, user_object_store_resolver=user_object_store_resolver)

    def to_dict(self, object_store_uris: Optional[Set[str]] = None) -> Dict[str, Any]:
        as_dict = super().to_dict()
        as_dict["global_max_percent_full"] = self.global_max_percent_full
        as_dict["search_for_missing"] = self.search_for_missing
        backends: List[Dict[str, Any]] = []
        for backend_id, backend in self.backends.items():
            backend_as_dict = backend.to_dict()
            backend_as_dict["id"] = backend_id
            backend_as_dict["max_percent_full"] = self.max_percent_full[backend_id]
            backend_as_dict["weight"] = len([i for i in self.original_weighted_backend_ids if i == backend_id])
            backends.append(backend_as_dict)
        if object_store_uris:
            for user_object_store_uri in object_store_uris:
                if not self.user_object_store_resolver:
                    raise ConfigDoesNotAllowException()

                object_store_config = self.user_object_store_resolver.resolve_object_store_uri_config(
                    user_object_store_uri
                )
                dynamic_object_store_as_dict = user_object_store_configuration_to_config_dict(
                    object_store_config, user_object_store_uri
                )
                backends.append(dynamic_object_store_as_dict)

        as_dict["backends"] = backends
        return as_dict

    def shutdown(self):
        """Shut down. Kill the free space monitor if there is one."""
        super().shutdown()
        if self.sleeper is not None:
            self.sleeper.wake()

    def __filesystem_monitor(self, sleeper: Sleeper):
        while self.running:
            new_weighted_backend_ids = self.original_weighted_backend_ids
            for id, backend in self.backends.items():
                maxpct = self.max_percent_full[id] or self.global_max_percent_full
                pct = backend.get_store_usage_percent()
                if pct > maxpct:
                    new_weighted_backend_ids = [_ for _ in new_weighted_backend_ids if _ != id]
            self.weighted_backend_ids = new_weighted_backend_ids
            sleeper.sleep(120)  # Test free space every 2 minutes

    def _construct_path(self, obj, **kwargs):
        return self._resolve_backend(obj.object_store_id).construct_path(obj, **kwargs)

    def _create(self, obj, **kwargs):
        """The only method in which obj.object_store_id may be None."""
        object_store_id = obj.object_store_id
        if object_store_id is None or not self._exists(obj, **kwargs):
            if object_store_id is None or (object_store_id not in self.backends and "://" not in object_store_id):
                try:
                    object_store_id = random.choice(self.weighted_backend_ids)
                    obj.object_store_id = object_store_id
                except IndexError:
                    raise ObjectInvalid(
                        f"objectstore.create, could not generate obj.object_store_id: {obj}, kwargs: {kwargs}"
                    )
                log.debug(
                    "Selected backend '%s' for creation of %s %s", object_store_id, obj.__class__.__name__, obj.id
                )
            else:
                log.debug(
                    "Using preferred backend '%s' for creation of %s %s",
                    object_store_id,
                    obj.__class__.__name__,
                    obj.id,
                )
            return self._resolve_backend(object_store_id).create(obj, **kwargs)
        else:
            return self._resolve_backend(object_store_id)

    def _call_method(self, method, obj, default, default_is_exception, **kwargs):
        object_store_id = self.__get_store_id_for(obj, **kwargs)
        if object_store_id is not None:
            return self._resolve_backend(object_store_id).__getattribute__(method)(obj, **kwargs)
        if default_is_exception:
            raise default(
                f"objectstore, _call_method failed: {method} on {self._repr_object_for_exception(obj)}, kwargs: {kwargs}"
            )
        else:
            return default

    def _resolve_backend(self, object_store_id: str):
        try:
            return self.backends[object_store_id]
        except KeyError:
            if is_user_object_store(object_store_id) and self.user_object_store_resolver:
                return self.user_object_store_resolver.resolve_object_store_uri(object_store_id)
            raise

    def get_quota_source_map(self) -> "QuotaSourceMap":
        if self._quota_source_map is None:
            quota_source_map = QuotaSourceMap()
            self._merge_quota_source_map(quota_source_map, self)
            self._quota_source_map = quota_source_map
        assert self._quota_source_map is not None
        return self._quota_source_map

    def get_device_source_map(self) -> "DeviceSourceMap":
        if self._device_source_map is None:
            device_source_map = DeviceSourceMap()
            self._merge_device_source_map(device_source_map, self)
            self._device_source_map = device_source_map
        assert self._device_source_map is not None
        return self._device_source_map

    @classmethod
    def _merge_quota_source_map(clz, quota_source_map, object_store):
        for backend_id, backend in object_store.backends.items():
            if isinstance(backend, DistributedObjectStore):
                clz._merge_quota_source_map(quota_source_map, backend)
            else:
                quota_source_map.backends[backend_id] = backend.get_quota_source_map()

    @classmethod
    def _merge_device_source_map(clz, device_source_map: "DeviceSourceMap", object_store):
        for backend_id, backend in object_store.backends.items():
            if isinstance(backend, DistributedObjectStore):
                clz._merge_device_source_map(device_source_map, backend)
            else:
                device_source_map.backends[backend_id] = backend.get_device_source_map()

    def __get_store_id_for(self, obj, **kwargs):
        if obj.object_store_id is not None:
            if obj.object_store_id in self.backends or is_user_object_store(obj.object_store_id):
                return obj.object_store_id
            else:
                log.warning(
                    "The backend object store ID (%s) for %s object with ID %s is invalid",
                    obj.object_store_id,
                    obj.__class__.__name__,
                    obj.id,
                )
        elif self.search_for_missing:
            # if this instance has been switched from a non-distributed to a
            # distributed object store, or if the object's store id is invalid,
            # try to locate the object
            for id, store in self.backends.items():
                if store.exists(obj, **kwargs):
                    log.warning(
                        f"{obj.__class__.__name__} object with ID {obj.id} found in backend object store with ID {id}"
                    )
                    obj.object_store_id = id
                    return id
        return None

    def object_store_ids(self, private=None):
        object_store_ids = []
        for backend_id, backend in self.backends.items():
            object_store_ids.extend(backend.object_store_ids(private=private))
            if backend.private is private or private is None:
                object_store_ids.append(backend_id)
        return object_store_ids

    def object_store_allows_id_selection(self) -> bool:
        """Return True if this object store respects object_store_id and allow selection of this."""
        return self.allow_user_selection

    def validate_selected_object_store_id(self, user, object_store_id: Optional[str]) -> Optional[str]:
        parent_check = super().validate_selected_object_store_id(user, object_store_id)
        if parent_check or object_store_id is None:
            return parent_check
        # user selection allowed and object_store_id is not None
        if is_user_object_store(object_store_id):
            if not user:
                return "Supplied object store id is not accessible"
            rest_of_uri = object_store_id.split("://", 1)[1]
            user_object_store_uuid = rest_of_uri
            for user_object_store in user.object_stores:
                if str(user_object_store.uuid) == user_object_store_uuid:
                    return None
            return "Supplied object store id was not found"
        if object_store_id not in self.object_store_ids_allowing_selection():
            return "Supplied object store id is not an allowed object store selection"
        return None

    def object_store_ids_allowing_selection(self) -> List[str]:
        """Return a non-empty list of allowed selectable object store IDs during creation."""
        return self.user_selection_allowed

    def get_concrete_store_by_object_store_id(self, object_store_id: str) -> Optional["ConcreteObjectStore"]:
        """If this is a distributed object store, get ConcreteObjectStore by object_store_id."""
        return self.backends[object_store_id]


class HierarchicalObjectStore(NestedObjectStore):
    """
    ObjectStore that defers to a list of backends.

    When getting objects the first store where the object exists is used.
    When creating objects only the first store is used.
    """

    store_type = "hierarchical"

    def __init__(self, config, config_dict, fsmon=False):
        """The default constructor. Extends `NestedObjectStore`."""
        super().__init__(config, config_dict)

        backends: Dict[int, ObjectStore] = {}
        is_private = config_dict.get("private", DEFAULT_PRIVATE)
        for order, backend_def in enumerate(config_dict["backends"]):
            backend_is_private = backend_def.get("private")
            if backend_is_private is not None:
                assert (
                    is_private == backend_is_private
                ), "The private attribute must be defined on the HierarchicalObjectStore and not contained concrete objectstores."
            backend_quota = backend_def.get("quota")
            if backend_quota is not None:
                # Make sure just was using defaults - because cannot override what is
                # is setup by the HierarchicalObjectStore.
                assert backend_quota.get("source", DEFAULT_QUOTA_SOURCE) == DEFAULT_QUOTA_SOURCE
                assert backend_quota.get("enabled", DEFAULT_QUOTA_ENABLED) == DEFAULT_QUOTA_ENABLED

            backends[order] = build_object_store_from_config(config, config_dict=backend_def, fsmon=fsmon)

        self.backends = backends
        self.private = is_private
        quota_config = config_dict.get("quota", {})
        self.quota_source = quota_config.get("source", DEFAULT_QUOTA_SOURCE)
        self.quota_enabled = quota_config.get("enabled", DEFAULT_QUOTA_ENABLED)

    @classmethod
    def parse_xml(clazz, config_xml):
        backends_list = []
        is_private = BaseObjectStore.parse_private_from_config_xml(config_xml)
        for backend in sorted(config_xml.find("backends"), key=lambda b: int(b.get("order"))):
            store_type = backend.get("type")
            objectstore_class, _ = type_to_object_store_class(store_type)
            backend_config_dict = objectstore_class.parse_xml(backend)
            backend_config_dict["private"] = is_private
            backend_config_dict["type"] = store_type
            backends_list.append(backend_config_dict)

        config_dict = {"backends": backends_list}
        config_dict["private"] = is_private
        return config_dict

    def to_dict(self):
        as_dict = super().to_dict()
        backends = []
        for backend in self.backends.values():
            backend_as_dict = backend.to_dict()
            backends.append(backend_as_dict)
        as_dict["backends"] = backends
        as_dict["private"] = self.private
        return as_dict

    def _exists(self, obj, **kwargs):
        """Check all child object stores."""
        for store in self.backends.values():
            if store.exists(obj, **kwargs):
                return True
        return False

    def _construct_path(self, obj, **kwargs):
        return self.backends[0].construct_path(obj, **kwargs)

    def _create(self, obj, **kwargs):
        """Call the primary object store."""
        return self.backends[0].create(obj, **kwargs)

    def _is_private(self, obj):
        # Unlink the DistributedObjectStore - the HierarchicalObjectStore does not use
        # object_store_id - so all the contained object stores need to define is_private
        # the same way.
        return self.private

    def get_quota_source_map(self):
        quota_source_map = QuotaSourceMap(
            self.quota_source,
            self.quota_enabled,
        )
        return quota_source_map


def serialize_static_object_store_config(object_store: ObjectStore, object_store_uris: Set[str]) -> Dict[str, Any]:
    """Serialize a static object store configuration for database-less serialization.

    The database-less part here comes from the fact these are used in job directories
    during extended metadata collection. Any database/vault/app config details should
    be unpacked and the result should be an object store configuration that doesn't
    depend on those entities but which resolves to the same locations.
    """
    if len(object_store_uris) == 0:
        return object_store.to_dict()
    if not isinstance(object_store, DistributedObjectStore):
        # TODO: Not for the MVP or first iteration - but potentially we could allow
        # a concrete store here and then build a Distributed store from that and
        # concrete stores represented by object_store_uris
        raise ConfigDoesNotAllowException("ObjectStore configuration does not allow per-user object stores")
    return object_store.to_dict(object_store_uris=object_store_uris)


class QuotaModel(BaseModel):
    source: Optional[str] = None
    enabled: bool


class ConcreteObjectStoreModel(BaseModel):
    object_store_id: Optional[str] = None
    private: bool
    name: Optional[str] = None
    description: Optional[str] = None
    quota: QuotaModel
    badges: List[BadgeDict]
    device: Optional[str] = None


def type_to_object_store_class(
    store: str, fsmon: bool = False, user_object_store_resolver: Optional[UserObjectStoreResolver] = None
) -> Tuple[Type[BaseObjectStore], Dict[str, Any]]:
    objectstore_class: Type[BaseObjectStore]
    objectstore_constructor_kwds: Dict[str, Any] = {}
    if store == "disk":
        objectstore_class = DiskObjectStore
    elif store == "boto3":
        from .s3_boto3 import S3ObjectStore as Boto3ObjectStore

        objectstore_class = Boto3ObjectStore
    elif store in ["s3", "aws_s3"]:
        from .s3 import S3ObjectStore

        objectstore_class = S3ObjectStore
    elif store == "cloud":
        from .cloud import Cloud

        objectstore_class = Cloud
    elif store in ["swift", "generic_s3"]:
        from .s3 import GenericS3ObjectStore

        objectstore_class = GenericS3ObjectStore
    elif store == "distributed":
        objectstore_class = DistributedObjectStore
        objectstore_constructor_kwds["fsmon"] = fsmon
        objectstore_constructor_kwds["user_object_store_resolver"] = user_object_store_resolver
    elif store == "hierarchical":
        objectstore_class = HierarchicalObjectStore
        objectstore_constructor_kwds["fsmon"] = fsmon
    elif store == "irods":
        from .irods import IRODSObjectStore

        objectstore_class = IRODSObjectStore
    elif store == "azure_blob":
        from .azure_blob import AzureBlobObjectStore

        objectstore_class = AzureBlobObjectStore
    elif store == "pithos":
        from .pithos import PithosObjectStore

        objectstore_class = PithosObjectStore
    elif store == "rucio":
        from .rucio import RucioObjectStore

        objectstore_class = RucioObjectStore
    elif store == "onedata":
        from .onedata import OnedataObjectStore

        objectstore_class = OnedataObjectStore
    else:
        raise Exception(f"Unrecognized object store definition: {store}")
    # Disable the Pulsar object store for now until it receives some attention
    # elif store == 'pulsar':
    #    from .pulsar import PulsarObjectStore
    #    return PulsarObjectStore(config=config, config_xml=config_xml)

    return objectstore_class, objectstore_constructor_kwds


def build_test_object_store_from_user_config(
    config,
    object_store_config: ObjectStoreConfiguration,
):
    # check an object store configuration by building a standalone object store
    # from a supplied user object store configuration.
    config_dict = user_object_store_configuration_to_config_dict(object_store_config, uuid4().hex)
    object_store = build_object_store_from_config(
        config,
        config_dict=config_dict,
        disable_process_management=True,
    )
    return object_store


def build_object_store_from_config(
    config,
    fsmon=False,
    config_xml=None,
    config_dict=None,
    disable_process_management=False,
    user_object_store_resolver: Optional[UserObjectStoreResolver] = None,
):
    """
    Invoke the appropriate object store.

    Will use the `object_store_config_file` attribute of the `config` object to
    configure a new object store from the specified XML file.

    Or you can specify the object store type in the `object_store` attribute of
    the `config` object. Currently 'disk', 's3', 'swift', 'distributed',
    'hierarchical', 'irods', and 'pulsar' are supported values.
    """
    from_object = "xml"

    if config is None and config_dict is not None and "config" in config_dict:
        # Build an application config object from to_dict of an ObjectStore.
        config = Bunch(disable_process_management=disable_process_management, **config_dict["config"])
    elif config is None:
        raise Exception(
            "build_object_store_from_config sent None as config parameter and one cannot be recovered from config_dict"
        )

    if config_xml is None and config_dict is None:
        config_file = config.object_store_config_file
        if os.path.exists(config_file):
            log.debug("Reading object store config from file: %s", config_file)
            if config_file.endswith(".xml") or config_file.endswith(".xml.sample"):
                # This is a top level invocation of build_object_store_from_config, and
                # we have an object_store_conf.xml -- read the .xml and build
                # accordingly
                config_xml = parse_xml(config.object_store_config_file).getroot()
                store = config_xml.get("type")
            else:
                with open(config_file) as f:
                    config_dict = yaml.safe_load(f)
                from_object = "dict"
                store = config_dict.get("type")
        elif config.object_store_config:
            log.debug("Reading object store config from object_store_config option")
            from_object = "dict"
            config_dict = config.object_store_config
            store = config_dict.get("type")
        else:
            store = config.object_store
    elif config_xml is not None:
        store = config_xml.get("type")
    elif config_dict is not None:
        from_object = "dict"
        store = config_dict.get("type")

    objectstore_class, objectstore_constructor_kwds = type_to_object_store_class(
        store, fsmon=fsmon, user_object_store_resolver=user_object_store_resolver
    )
    if from_object == "xml":
        return objectstore_class.from_xml(config=config, config_xml=config_xml, **objectstore_constructor_kwds)
    else:
        return objectstore_class(config=config, config_dict=config_dict, **objectstore_constructor_kwds)


# View into the application configuration that is shared between the global object store
# and user defined object stores as produced by concrete_object_store.
class UserObjectStoresAppConfig(BaseModel):
    object_store_cache_path: str
    object_store_cache_size: int
    user_config_templates_use_saved_configuration: Literal["fallback", "preferred", "never"]
    jobs_directory: str
    new_file_path: str
    umask: int
    gid: int


# TODO: this will need app details...
# TODO: unit test from configuration dict...
def concrete_object_store(
    object_store_configuration: ObjectStoreConfiguration, app_config: UserObjectStoresAppConfig
) -> ConcreteObjectStore:
    # Adapt structured UserObjectStoresAppConfig into a more full configuration object as expected by
    # the object stores
    class GalaxyConfigAdapter:
        # Hard code these, these will not support legacy features
        object_store_check_old_style = False
        object_store_store_by = "uuid"

        # Set this to false for now... not sure but we may want to revisit this
        enable_quotas = False

        # These need to come in from Galaxy's config
        jobs_directory = app_config.jobs_directory
        new_file_path = app_config.new_file_path
        umask = app_config.umask
        gid = app_config.gid
        object_store_cache_size = app_config.object_store_cache_size
        object_store_cache_path = app_config.object_store_cache_path

    objectstore_class, objectstore_constructor_kwds = type_to_object_store_class(
        store=object_store_configuration.type,
        fsmon=False,
    )
    assert issubclass(objectstore_class, ConcreteObjectStore)
    return objectstore_class(
        config=GalaxyConfigAdapter(),
        config_dict=object_store_configuration.model_dump(),
        **objectstore_constructor_kwds,
    )


def local_extra_dirs(func):
    """Non-local plugin decorator using local directories for the extra_dirs (job_work and temp)."""

    def wraps(self, *args, **kwargs):
        if kwargs.get("base_dir", None) is None:
            return func(self, *args, **kwargs)
        else:
            for c in self.__class__.__mro__:
                if c.__name__ == "DiskObjectStore":
                    return getattr(c, func.__name__)(self, *args, **kwargs)
            raise Exception(
                f"Could not call DiskObjectStore's {func.__name__} method, does your "
                "Object Store plugin inherit from DiskObjectStore?"
            )

    return wraps


def config_to_dict(config):
    """Dict-ify the portion of a config object consumed by the ObjectStore class and its subclasses."""
    return {
        "object_store_check_old_style": config.object_store_check_old_style,
        "enable_quotas": config.enable_quotas,
        "file_path": config.file_path,
        "umask": config.umask,
        "jobs_directory": config.jobs_directory,
        "new_file_path": config.new_file_path,
        "object_store_cache_path": config.object_store_cache_path,
        "object_store_cache_size": config.object_store_cache_size,
        "gid": config.gid,
    }


class QuotaSourceInfo(NamedTuple):
    label: Optional[str]
    use: bool


class DeviceSourceMap:
    def __init__(self, device_id=DEFAULT_DEVICE_ID):
        self.default_device_id = device_id
        self.backends = {}

    def get_device_id(self, object_store_id: str) -> Optional[str]:
        if object_store_id in self.backends:
            device_map = self.backends.get(object_store_id)
            if device_map:
                print(device_map)
                return device_map.get_device_id(object_store_id)

        return self.default_device_id


class QuotaSourceMap:
    def __init__(self, source=DEFAULT_QUOTA_SOURCE, enabled=DEFAULT_QUOTA_ENABLED):
        self.default_quota_source = source
        self.default_quota_enabled = enabled
        self.info = QuotaSourceInfo(self.default_quota_source, self.default_quota_enabled)
        # User defined sources are provided by the user and the quota is not tracked
        self.user_defined_source_info = QuotaSourceInfo(label=None, use=False)
        self.backends = {}
        self._labels = None

    def get_quota_source_info(self, object_store_id: Optional[str]) -> QuotaSourceInfo:
        if object_store_id in self.backends:
            return self.backends[object_store_id].get_quota_source_info(object_store_id)
        elif is_user_object_store(object_store_id):
            return self.user_defined_source_info
        else:
            return self.info

    def get_quota_source_label(self, object_store_id):
        if object_store_id in self.backends:
            return self.backends[object_store_id].get_quota_source_label(object_store_id)
        else:
            return self.default_quota_source

    def get_quota_source_labels(self):
        if self._labels is None:
            labels = set()
            if self.default_quota_source:
                labels.add(self.default_quota_source)
            for backend in self.backends.values():
                labels = labels.union(backend.get_quota_source_labels())
            self._labels = labels
        return self._labels

    def default_usage_excluded_ids(self):
        exclude_object_store_ids = []
        for backend_id, backend_source_map in self.backends.items():
            if backend_source_map.default_quota_source is not None:
                exclude_object_store_ids.append(backend_id)
            elif not backend_source_map.default_quota_enabled:
                exclude_object_store_ids.append(backend_id)
        return exclude_object_store_ids

    def get_id_to_source_pairs(self, include_default_quota_source=False):
        pairs = []
        for backend_id, backend_source_map in self.backends.items():
            if (
                backend_source_map.default_quota_source is not None or include_default_quota_source
            ) and backend_source_map.default_quota_enabled:
                pairs.append((backend_id, backend_source_map.default_quota_source))
        return pairs

    def ids_per_quota_source(self, include_default_quota_source=False):
        quota_sources: Dict[Optional[str], List[str]] = {}
        for object_id, quota_source_label in self.get_id_to_source_pairs(
            include_default_quota_source=include_default_quota_source
        ):
            if quota_source_label not in quota_sources:
                quota_sources[quota_source_label] = []
            quota_sources[quota_source_label].append(object_id)
        return quota_sources


class ObjectCreationProblem(Exception):
    pass


# Calling these client_message to make it clear they should use the language of the
# Galaxy UI/UX - for instance "storage location" not "objectstore".
class ObjectCreationProblemSharingDisabled(ObjectCreationProblem):
    client_message = "Job attempted to create sharable output datasets in a storage location with sharing disabled"


class ObjectCreationProblemStoreFull(ObjectCreationProblem):
    client_message = (
        "Job attempted to create output datasets in a full storage location, please contact your admin for more details"
    )


class ObjectStorePopulator:
    """Small helper for interacting with the object store and making sure all
    datasets from a job end up with the same object_store_id.
    """

    def __init__(self, has_object_store, user):
        if hasattr(has_object_store, "object_store"):
            object_store = has_object_store.object_store
        else:
            object_store = has_object_store
        self.object_store = object_store
        self.object_store_id = None
        self.user = user

    def set_object_store_id(self, data, require_shareable=False):
        self.set_dataset_object_store_id(data.dataset, require_shareable=require_shareable)

    def set_dataset_object_store_id(self, dataset, require_shareable=True):
        # Create an empty file immediately.  The first dataset will be
        # created in the "default" store, all others will be created in
        # the same store as the first.
        dataset.object_store_id = self.object_store_id
        try:
            ensure_non_private = require_shareable
            concrete_store = self.object_store.create(dataset, ensure_non_private=ensure_non_private)
            if concrete_store.private and require_shareable:
                raise ObjectCreationProblemSharingDisabled()
        except ObjectInvalid:
            raise ObjectCreationProblemStoreFull()
        self.object_store_id = dataset.object_store_id  # these will be the same thing after the first output


def persist_extra_files(
    object_store: ObjectStore,
    src_extra_files_path: str,
    primary_data: "DatasetInstance",
    extra_files_path_name: Optional[str] = None,
) -> None:
    if not primary_data.dataset.purged and os.path.exists(src_extra_files_path):
        assert primary_data.dataset
        if not extra_files_path_name:
            extra_files_path_name = primary_data.dataset.extra_files_path_name_from(object_store)
        assert extra_files_path_name
        persist_extra_files_for_dataset(object_store, src_extra_files_path, primary_data.dataset, extra_files_path_name)


def persist_extra_files_for_dataset(
    object_store: ObjectStore,
    src_extra_files_path: str,
    dataset: "Dataset",
    extra_files_path_name: str,
):
    for root, _dirs, files in safe_walk(src_extra_files_path):
        extra_dir = os.path.join(extra_files_path_name, os.path.relpath(root, src_extra_files_path))
        extra_dir = os.path.normpath(extra_dir)
        for f in files:
            if not in_directory(f, src_extra_files_path):
                # Unclear if this can ever happen if we use safe_walk ... probably not ?
                raise MalformedContents(f"Invalid dataset path: {f}")
            object_store.update_from_file(
                dataset,
                extra_dir=extra_dir,
                alt_name=f,
                file_name=os.path.join(root, f),
                create=True,
                preserve_symlinks=True,
            )
