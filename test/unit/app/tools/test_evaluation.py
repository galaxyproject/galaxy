import os
from unittest import TestCase

from galaxy.app_unittest_utils.tools_support import UsesApp
from galaxy.job_execution.compute_environment import SimpleComputeEnvironment
from galaxy.job_execution.datasets import DatasetPath
from galaxy.model import (
    Dataset,
    History,
    HistoryDatasetAssociation,
    Job,
    JobParameter,
    JobToInputDatasetAssociation,
    JobToOutputDatasetAssociation,
)
from galaxy.tool_util.parser.output_objects import ToolOutput
from galaxy.tools.evaluation import ToolEvaluator

# For MockTool
from galaxy.tools.parameters import params_from_strings
from galaxy.tools.parameters.basic import (
    DataToolParameter,
    IntegerToolParameter,
    SelectToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    ConditionalWhen,
    Repeat,
)
from galaxy.util import XML
from galaxy.util.bunch import Bunch

# To Test:
# - param_file handling.
TEST_TOOL_DIRECTORY = "/path/to/the/tool"
TEST_GALAXY_URL = "http://mycool.galaxyproject.org:8456"


class ToolEvaluatorTestCase(TestCase, UsesApp):
    def setUp(self):
        self.setup_app()
        self.tool = MockTool(self.app)
        self.job = Job()
        self.job.history = History()
        self.job.history.id = 42
        self.job.parameters = [JobParameter(name="thresh", value="4")]
        self.evaluator = ToolEvaluator(self.app, self.tool, self.job, self.test_directory)

    def tearDown(self):
        self.tear_down_app()

    def test_simple_evaluation(self):
        self._setup_test_bwa_job()
        self._set_compute_environment()
        command_line = self.evaluator.build()[0]
        self.assertEqual(
            command_line, "bwa --thresh=4 --in=/galaxy/files/dataset_1.dat --out=/galaxy/files/dataset_2.dat"
        )

    def test_repeat_evaluation(self):
        repeat = Repeat()
        repeat.name = "r"
        repeat.inputs = {"thresh": self.tool.test_thresh_param()}
        self.tool.set_params({"r": repeat})
        self.job.parameters = [
            JobParameter(name="r", value="""[{"thresh": 4, "__index__": 0},{"thresh": 5, "__index__": 1}]""")
        ]
        self.tool._command_line = "prog1 #for $r_i in $r # $r_i.thresh#end for#"
        self._set_compute_environment()
        command_line = self.evaluator.build()[0]
        self.assertEqual(command_line, "prog1  4 5")

    def test_eval_galaxy_url(self):
        self.tool._command_line = "prog1 $__galaxy_url__"
        self._set_compute_environment()
        command_line = self.evaluator.build()[0]
        self.assertEqual(command_line, "prog1 %s" % TEST_GALAXY_URL)

    def test_eval_history_id(self):
        self.tool._command_line = "prog1 '$__history_id__'"
        self._set_compute_environment()
        command_line = self.evaluator.build()[0]
        self.assertEqual(command_line, "prog1 '%s'" % self.app.security.encode_id(42))

    def test_conditional_evaluation(self):
        select_xml = XML("""<param name="always_true" type="select"><option value="true">True</option></param>""")
        parameter = SelectToolParameter(self.tool, select_xml)

        conditional = Conditional()
        conditional.name = "c"
        conditional.test_param = parameter
        when = ConditionalWhen()
        when.inputs = {"thresh": self.tool.test_thresh_param()}
        when.value = "true"
        conditional.cases = [when]
        self.tool.set_params({"c": conditional})
        self.job.parameters = [
            JobParameter(name="c", value="""{"thresh": 4, "always_true": "true", "__current_case__": 0}""")
        ]
        self.tool._command_line = "prog1 --thresh=${c.thresh} --test_param=${c.always_true}"
        self._set_compute_environment()
        command_line = self.evaluator.build()[0]
        self.assertEqual(command_line, "prog1 --thresh=4 --test_param=true")

    def test_evaluation_of_optional_datasets(self):
        # Make sure optional dataset don't cause evaluation to break and
        # evaluate in cheetah templates as 'None'.
        select_xml = XML("""<param name="input1" type="data" optional="true"></param>""")
        parameter = DataToolParameter(self.tool, select_xml)
        self.job.parameters = [JobParameter(name="input1", value="null")]
        self.tool.set_params({"input1": parameter})
        self.tool._command_line = "prog1 --opt_input='${input1}'"
        self._set_compute_environment()
        command_line = self.evaluator.build()[0]
        self.assertEqual(command_line, "prog1 --opt_input='None'")

    def test_evaluation_with_path_rewrites_wrapped(self):
        self.tool.check_values = True
        self.__test_evaluation_with_path_rewrites()

    def test_evaluation_with_path_rewrites_unwrapped(self):
        self.tool.check_values = False
        self.__test_evaluation_with_path_rewrites()

    def __test_evaluation_with_path_rewrites(self):
        # Various things can cause dataset paths to be rewritten (Task
        # splitting, config.outputs_to_working_directory). This tests that
        # functionality.
        self._setup_test_bwa_job()
        job_path_1 = "%s/dataset_1.dat" % self.test_directory
        job_path_2 = "%s/dataset_2.dat" % self.test_directory
        self._set_compute_environment(
            input_paths=[DatasetPath(1, "/galaxy/files/dataset_1.dat", false_path=job_path_1)],
            output_paths=[DatasetPath(2, "/galaxy/files/dataset_2.dat", false_path=job_path_2)],
        )
        command_line = self.evaluator.build()[0]
        self.assertEqual(command_line, f"bwa --thresh=4 --in={job_path_1} --out={job_path_2}")

    def test_configfiles_evaluation(self):
        self.tool.config_files.append(("conf1", None, "$thresh"))
        self.tool._command_line = "prog1 $conf1"
        self._set_compute_environment()
        command_line, _, extra_filenames, _ = self.evaluator.build()
        self.assertEqual(len(extra_filenames), 1)
        config_filename = extra_filenames[0]
        config_basename = os.path.basename(config_filename)
        # Verify config file written into working directory.
        self.assertEqual(os.path.join(self.test_directory, "configs", config_basename), config_filename)
        # Verify config file contents are evaluated against parameters.
        assert open(config_filename).read() == "4"
        self.assertEqual(command_line, "prog1 %s" % config_filename)

    def test_arbitrary_path_rewriting_wrapped(self):
        self.tool.check_values = True
        self.__test_arbitrary_path_rewriting()

    def test_arbitrary_path_rewriting_unwrapped(self):
        self.tool.check_values = False
        self.__test_arbitrary_path_rewriting()

    def __test_arbitrary_path_rewriting(self):
        self.job.parameters = [JobParameter(name="index_path", value='"/old/path/human"')]
        xml = XML(
            """<param name="index_path" type="select">
            <option value="/old/path/human">Human</option>
            <option value="/old/path/mouse">Mouse</option>
        </param>"""
        )
        parameter = SelectToolParameter(self.tool, xml)

        def get_field_by_name_for_value(name, value, trans, other_values):
            assert value == "/old/path/human"
            assert name == "path"
            return ["/old/path/human"]

        def get_options(trans, other_values):
            return [["", "/old/path/human", ""]]

        parameter.options = Bunch(get_field_by_name_for_value=get_field_by_name_for_value, get_options=get_options)
        self.tool.set_params({"index_path": parameter})
        self.tool._command_line = "prog1 $index_path.fields.path"
        self._set_compute_environment(unstructured_path_rewrites={"/old": "/new"})
        command_line = self.evaluator.build()[0]
        self.assertEqual(command_line, "prog1 /new/path/human")

    def test_version_command(self):
        self.tool.version_string_cmd = "echo v.1.1"
        self._setup_test_bwa_job()
        self._set_compute_environment()
        version_command_line = self.evaluator.build()[1]
        assert self.tool.version_string_cmd in version_command_line

    def test_template_property_app(self):
        self._assert_template_property_is("$__app__.config.new_file_path", self.app.config.new_file_path)

    def test_template_property_new_file_path(self):
        self._assert_template_property_is("$__new_file_path__", self.app.config.new_file_path)

    def test_template_property_root_dir(self):
        self._assert_template_property_is("$__root_dir__", self.app.config.root)

    def test_template_property_admin_users(self):
        self._assert_template_property_is("$__admin_users__", "mary@example.com")

    def _assert_template_property_is(self, expression, value):
        self.tool._command_line = "test.exe"
        self.tool.config_files.append(("conf1", None, """%s""" % expression))
        self._set_compute_environment()
        extra_filenames = self.evaluator.build()[2]
        config_filename = extra_filenames[0]
        self.assertEqual(open(config_filename).read(), value)

    def _set_compute_environment(self, **kwds):
        if "working_directory" not in kwds:
            kwds["working_directory"] = self.test_directory
        if "new_file_path" not in kwds:
            kwds["new_file_path"] = self.app.config.new_file_path
        self.evaluator.set_compute_environment(ComputeEnvironment(**kwds))  # type: ignore[arg-type]
        assert "exec_before_job" in self.tool.hooks_called

    def _setup_test_bwa_job(self):
        def hda(id, name, path):
            hda = HistoryDatasetAssociation(name=name, metadata=dict())
            hda.dataset = Dataset(id=id, external_filename=path)
            return hda

        id, name, path = 111, "input1", "/galaxy/files/dataset_1.dat"
        self.job.input_datasets = [JobToInputDatasetAssociation(name=name, dataset=hda(id, name, path))]

        id, name, path = 112, "output1", "/galaxy/files/dataset_2.dat"
        self.job.output_datasets = [JobToOutputDatasetAssociation(name=name, dataset=hda(id, name, path))]


class MockHistoryDatasetAssociation(HistoryDatasetAssociation):
    def __init__(self, **kwds):
        self._metadata = dict()
        super().__init__(**kwds)


class ComputeEnvironment(SimpleComputeEnvironment):
    def __init__(
        self, new_file_path, working_directory, input_paths=None, output_paths=None, unstructured_path_rewrites=None
    ):
        if input_paths is None:
            input_paths = ["/galaxy/files/dataset_1.dat"]
        if output_paths is None:
            output_paths = ["/galaxy/files/dataset_2.dat"]
        self._new_file_path = new_file_path
        self._working_directory = working_directory
        self._input_paths = input_paths
        self._output_paths = output_paths
        self._unstructured_path_rewrites = unstructured_path_rewrites or {}

    def input_paths(self):
        return self._input_paths

    def input_path_rewrite(self, dataset):
        path = self._input_paths[0]
        return path.false_path if hasattr(path, "false_path") else path

    def output_path_rewrite(self, dataset):
        path = self._output_paths[0]
        return path.false_path if hasattr(path, "false_path") else path

    def output_paths(self):
        return self._output_paths

    def working_directory(self):
        return self._working_directory

    def home_directory(self):
        return self._working_directory

    def tmp_directory(self):
        return self._working_directory

    def new_file_path(self):
        return self._new_file_path

    def unstructured_path_rewrite(self, path):
        for key, val in self._unstructured_path_rewrites.items():
            if path.startswith(key):
                return path.replace(key, val)
        return None

    def tool_directory(self):
        return TEST_TOOL_DIRECTORY

    def galaxy_url(self):
        return TEST_GALAXY_URL

    def version_path(self):
        return "tool_version"

    def get_file_sources_dict(self):
        return {}


class MockTool:
    def __init__(self, app):
        self.profile = 16.01
        self.python_template_version = "2.7"
        self.app = app
        self.hooks_called = []
        self.environment_variables = []
        self._config_files = []
        self._command_line = "bwa --thresh=$thresh --in=$input1 --out=$output1"
        self._params = {"thresh": self.test_thresh_param()}
        self.options = Bunch(sanitize=False)
        self.check_values = True
        self.version_string_cmd = ""

    def test_thresh_param(self):
        elem = XML('<param name="thresh" type="integer" value="5" />')
        return IntegerToolParameter(self, elem)

    def params_from_strings(self, params, app, ignore_errors=False):
        return params_from_strings(self.inputs, params, app, ignore_errors)

    @property
    def config_file(self):
        return "<fake tool>"

    @property
    def template_macro_params(self):
        return {}

    @property
    def inputs(self):
        return self._params

    def set_params(self, params):
        self._params = params

    @property
    def outputs(self):
        return dict(
            output1=ToolOutput("output1"),
        )

    @property
    def tmp_directory_vars(self):
        return ["TMP"]

    @property
    def config_files(self):
        return self._config_files

    @property
    def command(self):
        return self._command_line

    @property
    def interpreter(self):
        return None

    def handle_unvalidated_param_values(self, input_values, app):
        pass

    def build_param_dict(self, incoming, *args, **kwds):
        return incoming

    def call_hook(self, hook_name, *args, **kwargs):
        self.hooks_called.append(hook_name)

    def exec_before_job(self, *args, **kwargs):
        pass
