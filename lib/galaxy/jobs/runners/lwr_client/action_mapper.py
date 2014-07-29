from json import load
from os import makedirs
from os.path import exists
from os.path import abspath
from os.path import dirname
from os.path import join
from os.path import basename
from os.path import sep
import fnmatch
from re import compile
from re import escape
import galaxy.util
from galaxy.util.bunch import Bunch
from .config_util import read_file
from .util import directory_files
from .util import unique_path_prefix
from .transport import get_file
from .transport import post_file


DEFAULT_MAPPED_ACTION = 'transfer'  # Not really clear to me what this should be, exception?
DEFAULT_PATH_MAPPER_TYPE = 'prefix'

STAGING_ACTION_REMOTE = "remote"
STAGING_ACTION_LOCAL = "local"
STAGING_ACTION_NONE = None
STAGING_ACTION_DEFAULT = "default"

# Poor man's enum.
path_type = Bunch(
    # Galaxy input datasets and extra files.
    INPUT="input",
    # Galaxy config and param files.
    CONFIG="config",
    # Files from tool's tool_dir (for now just wrapper if available).
    TOOL="tool",
    # Input work dir files - e.g. metadata files, task-split input files, etc..
    WORKDIR="workdir",
    # Galaxy output datasets in their final home.
    OUTPUT="output",
    # Galaxy from_work_dir output paths and other files (e.g. galaxy.json)
    OUTPUT_WORKDIR="output_workdir",
    # Other fixed tool parameter paths (likely coming from tool data, but not
    # nessecarily). Not sure this is the best name...
    UNSTRUCTURED="unstructured",
)


ACTION_DEFAULT_PATH_TYPES = [
    path_type.INPUT,
    path_type.CONFIG,
    path_type.TOOL,
    path_type.WORKDIR,
    path_type.OUTPUT,
    path_type.OUTPUT_WORKDIR,
]
ALL_PATH_TYPES = ACTION_DEFAULT_PATH_TYPES + [path_type.UNSTRUCTURED]


class FileActionMapper(object):
    """
    Objects of this class define how paths are mapped to actions.

    >>> json_string = r'''{"paths": [ \
      {"path": "/opt/galaxy", "action": "none"}, \
      {"path": "/galaxy/data", "action": "transfer"}, \
      {"path": "/cool/bamfiles/**/*.bam", "action": "copy", "match_type": "glob"}, \
      {"path": ".*/dataset_\\\\d+.dat", "action": "copy", "match_type": "regex"} \
    ]}'''
    >>> from tempfile import NamedTemporaryFile
    >>> from os import unlink
    >>> def mapper_for(default_action, config_contents):
    ...     f = NamedTemporaryFile(delete=False)
    ...     f.write(config_contents.encode('UTF-8'))
    ...     f.close()
    ...     mock_client = Bunch(default_file_action=default_action, action_config_path=f.name, files_endpoint=None)
    ...     mapper = FileActionMapper(mock_client)
    ...     mapper = FileActionMapper(config=mapper.to_dict()) # Serialize and deserialize it to make sure still works
    ...     unlink(f.name)
    ...     return mapper
    >>> mapper = mapper_for(default_action='none', config_contents=json_string)
    >>> # Test first config line above, implicit path prefix mapper
    >>> action = mapper.action('/opt/galaxy/tools/filters/catWrapper.py', 'input')
    >>> action.action_type == u'none'
    True
    >>> action.staging_needed
    False
    >>> # Test another (2nd) mapper, this one with a different action
    >>> action = mapper.action('/galaxy/data/files/000/dataset_1.dat', 'input')
    >>> action.action_type == u'transfer'
    True
    >>> action.staging_needed
    True
    >>> # Always at least copy work_dir outputs.
    >>> action = mapper.action('/opt/galaxy/database/working_directory/45.sh', 'workdir')
    >>> action.action_type == u'copy'
    True
    >>> action.staging_needed
    True
    >>> # Test glob mapper (matching test)
    >>> mapper.action('/cool/bamfiles/projectABC/study1/patient3.bam', 'input').action_type == u'copy'
    True
    >>> # Test glob mapper (non-matching test)
    >>> mapper.action('/cool/bamfiles/projectABC/study1/patient3.bam.bai', 'input').action_type == u'none'
    True
    >>> # Regex mapper test.
    >>> mapper.action('/old/galaxy/data/dataset_10245.dat', 'input').action_type == u'copy'
    True
    >>> # Doesn't map unstructured paths by default
    >>> mapper.action('/old/galaxy/data/dataset_10245.dat', 'unstructured').action_type == u'none'
    True
    >>> input_only_mapper = mapper_for(default_action="none", config_contents=r'''{"paths": [ \
      {"path": "/", "action": "transfer", "path_types": "input"} \
    ] }''')
    >>> input_only_mapper.action('/dataset_1.dat', 'input').action_type == u'transfer'
    True
    >>> input_only_mapper.action('/dataset_1.dat', 'output').action_type == u'none'
    True
    >>> unstructured_mapper = mapper_for(default_action="none", config_contents=r'''{"paths": [ \
      {"path": "/", "action": "transfer", "path_types": "*any*"} \
    ] }''')
    >>> unstructured_mapper.action('/old/galaxy/data/dataset_10245.dat', 'unstructured').action_type == u'transfer'
    True
    """

    def __init__(self, client=None, config=None):
        if config is None and client is None:
            message = "FileActionMapper must be constructed from either a client or a config dictionary."
            raise Exception(message)
        if config is None:
            config = self.__client_to_config(client)
        self.default_action = config.get("default_action", "transfer")
        self.mappers = mappers_from_dicts(config.get("paths", []))
        self.files_endpoint = config.get("files_endpoint", None)

    def action(self, path, type, mapper=None):
        mapper = self.__find_mapper(path, type, mapper)
        action_class = self.__action_class(path, type, mapper)
        file_lister = DEFAULT_FILE_LISTER
        action_kwds = {}
        if mapper:
            file_lister = mapper.file_lister
            action_kwds = mapper.action_kwds
        action = action_class(path, file_lister=file_lister, **action_kwds)
        self.__process_action(action, type)
        return action

    def unstructured_mappers(self):
        """ Return mappers that will map 'unstructured' files (i.e. go beyond
        mapping inputs, outputs, and config files).
        """
        return filter(lambda m: path_type.UNSTRUCTURED in m.path_types, self.mappers)

    def to_dict(self):
        return dict(
            default_action=self.default_action,
            files_endpoint=self.files_endpoint,
            paths=map(lambda m: m.to_dict(), self.mappers)
        )

    def __client_to_config(self, client):
        action_config_path = client.action_config_path
        if action_config_path:
            config = read_file(action_config_path)
        else:
            config = dict()
        config["default_action"] = client.default_file_action
        config["files_endpoint"] = client.files_endpoint
        return config

    def __load_action_config(self, path):
        config = load(open(path, 'rb'))
        self.mappers = mappers_from_dicts(config.get('paths', []))

    def __find_mapper(self, path, type, mapper=None):
        if not mapper:
            normalized_path = abspath(path)
            for query_mapper in self.mappers:
                if query_mapper.matches(normalized_path, type):
                    mapper = query_mapper
                    break
        return mapper

    def __action_class(self, path, type, mapper):
        action_type = self.default_action if type in ACTION_DEFAULT_PATH_TYPES else "none"
        if mapper:
            action_type = mapper.action_type
        if type in ["workdir", "output_workdir"] and action_type == "none":
            # We are changing the working_directory relative to what
            # Galaxy would use, these need to be copied over.
            action_type = "copy"
        action_class = actions.get(action_type, None)
        if action_class is None:
            message_template = "Unknown action_type encountered %s while trying to map path %s"
            message_args = (action_type, path)
            raise Exception(message_template % message_args)
        return action_class

    def __process_action(self, action, file_type):
        """ Extension point to populate extra action information after an
        action has been created.
        """
        if action.action_type == "remote_transfer":
            url_base = self.files_endpoint
            if not url_base:
                raise Exception("Attempted to use remote_transfer action with defining a files_endpoint")
            if "?" not in url_base:
                url_base = "%s?" % url_base
            # TODO: URL encode path.
            url = "%s&path=%s&file_type=%s" % (url_base, action.path, file_type)
            action.url = url

REQUIRED_ACTION_KWD = object()


class BaseAction(object):
    action_spec = {}

    def __init__(self, path, file_lister=None):
        self.path = path
        self.file_lister = file_lister or DEFAULT_FILE_LISTER

    def unstructured_map(self, path_helper):
        unstructured_map = self.file_lister.unstructured_map(self.path)
        if self.staging_needed:
            # To ensure uniqueness, prepend unique prefix to each name
            prefix = unique_path_prefix(self.path)
            for path, name in unstructured_map.iteritems():
                unstructured_map[path] = join(prefix, name)
        else:
            path_rewrites = {}
            for path in unstructured_map:
                rewrite = self.path_rewrite(path_helper, path)
                if rewrite:
                    path_rewrites[path] = rewrite
            unstructured_map = path_rewrites
        return unstructured_map

    @property
    def staging_needed(self):
        return self.staging != STAGING_ACTION_NONE

    @property
    def staging_action_local(self):
        return self.staging == STAGING_ACTION_LOCAL


class NoneAction(BaseAction):
    """ This action indicates the corresponding path does not require any
    additional action. This should indicate paths that are available both on
    the LWR client (i.e. Galaxy server) and remote LWR server with the same
    paths. """
    action_type = "none"
    staging = STAGING_ACTION_NONE

    def to_dict(self):
        return dict(path=self.path, action_type=self.action_type)

    @classmethod
    def from_dict(cls, action_dict):
        return NoneAction(path=action_dict["path"])

    def path_rewrite(self, path_helper, path=None):
        return None


class RewriteAction(BaseAction):
    """ This actin indicates the LWR server should simply rewrite the path
    to the specified file.
    """
    action_spec = dict(
        source_directory=REQUIRED_ACTION_KWD,
        destination_directory=REQUIRED_ACTION_KWD
    )
    action_type = "rewrite"
    staging = STAGING_ACTION_NONE

    def __init__(self, path, file_lister=None, source_directory=None, destination_directory=None):
        self.path = path
        self.file_lister = file_lister or DEFAULT_FILE_LISTER
        self.source_directory = source_directory
        self.destination_directory = destination_directory

    def to_dict(self):
        return dict(
            path=self.path,
            action_type=self.action_type,
            source_directory=self.source_directory,
            destination_directory=self.destination_directory,
        )

    @classmethod
    def from_dict(cls, action_dict):
        return RewriteAction(
            path=action_dict["path"],
            source_directory=action_dict["source_directory"],
            destination_directory=action_dict["destination_directory"],
        )

    def path_rewrite(self, path_helper, path=None):
        if not path:
            path = self.path
        new_path = path_helper.from_posix_with_new_base(self.path, self.source_directory, self.destination_directory)
        return None if new_path == self.path else new_path


class TransferAction(BaseAction):
    """ This actions indicates that the LWR client should initiate an HTTP
    transfer of the corresponding path to the remote LWR server before
    launching the job. """
    action_type = "transfer"
    staging = STAGING_ACTION_LOCAL


class CopyAction(BaseAction):
    """ This action indicates that the LWR client should execute a file system
    copy of the corresponding path to the LWR staging directory prior to
    launching the corresponding job. """
    action_type = "copy"
    staging = STAGING_ACTION_LOCAL


class RemoteCopyAction(BaseAction):
    """ This action indicates the LWR server should copy the file before
    execution via direct file system copy. This is like a CopyAction, but
    it indicates the action should occur on the LWR server instead of on
    the client.
    """
    action_type = "remote_copy"
    staging = STAGING_ACTION_REMOTE

    def to_dict(self):
        return dict(path=self.path, action_type=self.action_type)

    @classmethod
    def from_dict(cls, action_dict):
        return RemoteCopyAction(path=action_dict["path"])

    def write_to_path(self, path):
        galaxy.util.copy_to_path(open(self.path, "rb"), path)

    def write_from_path(self, lwr_path):
        destination = self.path
        parent_directory = dirname(destination)
        if not exists(parent_directory):
            makedirs(parent_directory)
        with open(lwr_path, "rb") as f:
            galaxy.util.copy_to_path(f, destination)


class RemoteTransferAction(BaseAction):
    """ This action indicates the LWR server should copy the file before
    execution via direct file system copy. This is like a CopyAction, but
    it indicates the action should occur on the LWR server instead of on
    the client.
    """
    action_type = "remote_transfer"
    staging = STAGING_ACTION_REMOTE

    def __init__(self, path, file_lister=None, url=None):
        super(RemoteTransferAction, self).__init__(path, file_lister=file_lister)
        self.url = url

    def to_dict(self):
        return dict(path=self.path, action_type=self.action_type, url=self.url)

    @classmethod
    def from_dict(cls, action_dict):
        return RemoteTransferAction(path=action_dict["path"], url=action_dict["url"])

    def write_to_path(self, path):
        get_file(self.url, path)

    def write_from_path(self, lwr_path):
        post_file(self.url, lwr_path)


class MessageAction(object):
    """ Sort of pseudo action describing "files" store in memory and
    transferred via message (HTTP, Python-call, MQ, etc...)
    """
    action_type = "message"
    staging = STAGING_ACTION_DEFAULT

    def __init__(self, contents, client=None):
        self.contents = contents
        self.client = client

    @property
    def staging_needed(self):
        return True

    @property
    def staging_action_local(self):
        # Ekkk, cannot be called if created through from_dict.
        # Shouldn't be a problem the way it is used - but is an
        # object design problem.
        return self.client.prefer_local_staging

    def to_dict(self):
        return dict(contents=self.contents, action_type=MessageAction.action_type)

    @classmethod
    def from_dict(cls, action_dict):
        return MessageAction(contents=action_dict["contents"])

    def write_to_path(self, path):
        open(path, "w").write(self.contents)


DICTIFIABLE_ACTION_CLASSES = [RemoteCopyAction, RemoteTransferAction, MessageAction]


def from_dict(action_dict):
    action_type = action_dict.get("action_type", None)
    target_class = None
    for action_class in DICTIFIABLE_ACTION_CLASSES:
        if action_type == action_class.action_type:
            target_class = action_class
    if not target_class:
        message = "Failed to recover action from dictionary - invalid action type specified %s." % action_type
        raise Exception(message)
    return target_class.from_dict(action_dict)


class BasePathMapper(object):

    def __init__(self, config):
        action_type = config.get('action', DEFAULT_MAPPED_ACTION)
        action_class = actions.get(action_type, None)
        action_kwds = action_class.action_spec.copy()
        for key, value in action_kwds.items():
            if key in config:
                action_kwds[key] = config[key]
            elif value is REQUIRED_ACTION_KWD:
                message_template = "action_type %s requires key word argument %s"
                message = message_template % (action_type, key)
                raise Exception(message)
        self.action_type = action_type
        self.action_kwds = action_kwds
        path_types_str = config.get('path_types', "*defaults*")
        path_types_str = path_types_str.replace("*defaults*", ",".join(ACTION_DEFAULT_PATH_TYPES))
        path_types_str = path_types_str.replace("*any*", ",".join(ALL_PATH_TYPES))
        self.path_types = path_types_str.split(",")
        self.file_lister = FileLister(config)

    def matches(self, path, path_type):
        path_type_matches = path_type in self.path_types
        return path_type_matches and self._path_matches(path)

    def _extend_base_dict(self, **kwds):
        base_dict = dict(
            action=self.action_type,
            path_types=",".join(self.path_types),
            match_type=self.match_type
        )
        base_dict.update(self.file_lister.to_dict())
        base_dict.update(self.action_kwds)
        base_dict.update(**kwds)
        return base_dict


class PrefixPathMapper(BasePathMapper):
    match_type = 'prefix'

    def __init__(self, config):
        super(PrefixPathMapper, self).__init__(config)
        self.prefix_path = abspath(config['path'])

    def _path_matches(self, path):
        return path.startswith(self.prefix_path)

    def to_pattern(self):
        pattern_str = "(%s%s[^\s,\"\']+)" % (escape(self.prefix_path), escape(sep))
        return compile(pattern_str)

    def to_dict(self):
        return self._extend_base_dict(path=self.prefix_path)


class GlobPathMapper(BasePathMapper):
    match_type = 'glob'

    def __init__(self, config):
        super(GlobPathMapper, self).__init__(config)
        self.glob_path = config['path']

    def _path_matches(self, path):
        return fnmatch.fnmatch(path, self.glob_path)

    def to_pattern(self):
        return compile(fnmatch.translate(self.glob_path))

    def to_dict(self):
        return self._extend_base_dict(path=self.glob_path)


class RegexPathMapper(BasePathMapper):
    match_type = 'regex'

    def __init__(self, config):
        super(RegexPathMapper, self).__init__(config)
        self.pattern_raw = config['path']
        self.pattern = compile(self.pattern_raw)

    def _path_matches(self, path):
        return self.pattern.match(path) is not None

    def to_pattern(self):
        return self.pattern

    def to_dict(self):
        return self._extend_base_dict(path=self.pattern_raw)

MAPPER_CLASSES = [PrefixPathMapper, GlobPathMapper, RegexPathMapper]
MAPPER_CLASS_DICT = dict(map(lambda c: (c.match_type, c), MAPPER_CLASSES))


def mappers_from_dicts(mapper_def_list):
    return map(lambda m: __mappper_from_dict(m), mapper_def_list)


def __mappper_from_dict(mapper_dict):
    map_type = mapper_dict.get('match_type', DEFAULT_PATH_MAPPER_TYPE)
    return MAPPER_CLASS_DICT[map_type](mapper_dict)


class FileLister(object):

    def __init__(self, config):
        self.depth = int(config.get("depth", "0"))

    def to_dict(self):
        return dict(
            depth=self.depth
        )

    def unstructured_map(self, path):
        depth = self.depth
        if self.depth == 0:
            return {path: basename(path)}
        else:
            while depth > 0:
                path = dirname(path)
                depth -= 1
            return dict([(join(path, f), f) for f in directory_files(path)])

DEFAULT_FILE_LISTER = FileLister(dict(depth=0))

ACTION_CLASSES = [
    NoneAction,
    RewriteAction,
    TransferAction,
    CopyAction,
    RemoteCopyAction,
    RemoteTransferAction,
]
actions = dict([(clazz.action_type, clazz) for clazz in ACTION_CLASSES])


__all__ = [
    FileActionMapper,
    path_type,
    from_dict,
    MessageAction,
    RemoteTransferAction,  # For testing
]
