from collections import namedtuple


# Job mock and helpers=======================================
class Job(object):
    def __init__(self):
        self.input_datasets = []
        self.input_library_datasets = []
        self.param_values = dict()
        self.parameters = []

    def get_param_values(self, app, ignore_errors=False):
        return self.param_values

    def set_arg_value(self, key, value):
        self.param_values[key] = value

    def add_input_dataset(self, dataset):
        self.input_datasets.append(dataset)

    def get_parameters(self):
        return self.parameters


class InputDataset(object):
    def __init__(self, name, dataset):
        self.name = name
        self.dataset = dataset


class NotAFile(object):
    pass


class Dataset(object):
    def __init__(self, file_name, file_ext, value):
        self.file_name = file_name
        self.datatype = Datatype(file_ext)
        self.ext = file_ext
        self.metadata = dict()
        self.metadata['sequences'] = value

    def get_metadata(self):
        return self.metadata


class Datatype(object):
    def __init__(self, file_ext):
        self.file_ext = file_ext


# Tool mock and helpers=========================================
class Tool(object):
    def __init__(self, id):
        self.old_id = id
        self.installed_tool_dependencies = []

    def add_tool_dependency(self, dependency):
        self.installed_tool_dependencies.append(dependency)


class ToolDependency(object):
    def __init__(self, name, dir_name):
        self.name = name
        self.dir_name = dir_name

    def installation_directory(self, app):
        return self.dir_name


# App mock=======================================================
class App(object):
    def __init__(self, tool_id, params):
        self.job_config = JobConfig(tool_id, params)


class JobConfig(object):
    def __init__(self, tool_id, params):
        self.info = namedtuple('info', ['id', 'nativeSpec', 'runner'])
        self.tool_id = tool_id
        self.nativeSpec = params
        self.default_id = "cluster_default"
        self.defNativeSpec = "-q test.q"
        self.defRunner = "drmaa"
        self.keys = {tool_id: self.info(self.tool_id, self.nativeSpec, self.defRunner),
                     "cluster_default": self.info(self.default_id, self.defNativeSpec, self.defRunner), }

    def get_destination(self, tool_id):
        invalid_destinations = ["cluster-kow", "destinationf", "thig",
                                "not_true_destination", "cluster_kow",
                                "Destination_3_med", "fake_destination",
                                "cluster_defaut", "even_lamerr_cluster",
                                "no_such_dest"]
        if tool_id in invalid_destinations:
            return None
        else:
            return tool_id


# JobMappingException mock=======================================
class JobMappingException(Exception):
    pass


class JobDestination(object):
    def __init__(self, **kwd):
        self.id = kwd.get('id')
        self.nativeSpec = kwd.get('params')['nativeSpecification']
        self.runner = kwd.get('runner')
