from simplejson import load
from os.path import abspath
from fnmatch import fnmatch
from re import compile


DEFAULT_MAPPED_ACTION = 'transfer'  # Not really clear to me what this should be, exception?
DEFAULT_PATH_MAPPER_TYPE = 'prefix'


class FileActionMapper(object):
    """
    Objects of this class define how paths are mapped to actions.

    >>> json_string = r'''{"paths": [ \
      {"path": "/opt/galaxy", "action": "none"}, \
      {"path": "/galaxy/data", "action": "transfer"}, \
      {"path": "/cool/bamfiles/**/*.bam", "action": "copy", "type": "glob"}, \
      {"path": ".*/dataset_\\\\d+.dat", "action": "copy", "type": "regex"} \
    ]}'''
    >>> from tempfile import NamedTemporaryFile
    >>> from os import unlink
    >>> f = NamedTemporaryFile(delete=False)
    >>> f.write(json_string)
    >>> f.close()
    >>> class MockClient():
    ...     default_file_action = 'none'
    ...     action_config_path = f.name
    ...
    >>> mapper = FileActionMapper(MockClient())
    >>> unlink(f.name)
    >>> # Test first config line above, implicit path prefix mapper
    >>> mapper.action('/opt/galaxy/tools/filters/catWrapper.py', 'input')
    ('none',)
    >>> # Test another (2nd) mapper, this one with a different action
    >>> mapper.action('/galaxy/data/files/000/dataset_1.dat', 'input')
    ('transfer',)
    >>> # Always at least copy work_dir outputs.
    >>> mapper.action('/opt/galaxy/database/working_directory/45.sh', 'work_dir')
    ('copy',)
    >>> # Test glob mapper (matching test)
    >>> mapper.action('/cool/bamfiles/projectABC/study1/patient3.bam', 'input')
    ('copy',)
    >>> # Test glob mapper (non-matching test)
    >>> mapper.action('/cool/bamfiles/projectABC/study1/patient3.bam.bai', 'input')
    ('none',)
    >>> # Regex mapper test.
    >>> mapper.action('/old/galaxy/data/dataset_10245.dat', 'input')
    ('copy',)
    """

    def __init__(self, client):
        self.default_action = client.default_file_action
        action_config_path = client.action_config_path
        self.mappers = []
        if action_config_path:
            self.__load_action_config(action_config_path)

    def __load_action_config(self, path):
        config = load(open(path, 'rb'))
        for path_config in config.get('paths', []):
            map_type = path_config.get('type', DEFAULT_PATH_MAPPER_TYPE)
            self.mappers.append(mappers[map_type](path_config))

    def action(self, path, type):
        action = self.default_action
        normalized_path = abspath(path)
        for mapper in self.mappers:
            if mapper.matches(normalized_path):
                action = mapper.action
                break
        if type in ["work_dir", "output_task"] and action == "none":
            ## We are changing the working_directory relative to what
            ## Galaxy would use, these need to be copied over.
            action = "copy"
        return (action,)


class BasePathMapper(object):

    def __init__(self, config):
        self.action = config.get('action', DEFAULT_MAPPED_ACTION)


class PrefixPathMapper(BasePathMapper):

    def __init__(self, config):
        super(PrefixPathMapper, self).__init__(config)
        self.prefix_path = abspath(config['path'])

    def matches(self, path):
        return path.startswith(self.prefix_path)


class GlobPathMapper(BasePathMapper):

    def __init__(self, config):
        super(GlobPathMapper, self).__init__(config)
        self.glob_path = config['path']

    def matches(self, path):
        return fnmatch(path, self.glob_path)


class RegexPathMapper(BasePathMapper):

    def __init__(self, config):
        super(RegexPathMapper, self).__init__(config)
        self.pattern = compile(config['path'])

    def matches(self, path):
        return self.pattern.match(path) is not None


mappers = {'prefix': PrefixPathMapper,
           'glob': GlobPathMapper,
           'regex': RegexPathMapper,
          }


__all__ = [FileActionMapper]
