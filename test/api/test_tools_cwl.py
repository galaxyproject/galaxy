"""Test CWL Tool Execution via the API."""

import json

from sys import platform as _platform

from base import api
from base.populators import DatasetPopulator
from base.populators import skip_without_tool

IS_OS_X = _platform == "darwin"


class CwlToolsTestCase( api.ApiTestCase ):
    """Test CWL Tool Execution via the API."""

    def setUp( self ):
        """Setup dataset populator."""
        super( CwlToolsTestCase, self ).setUp( )
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )

    @skip_without_tool( "cat1-tool" )
    def test_cat1_number( self ):
        """Test execution of cat1 using the "normal" Galaxy job API representation."""
        history_id = self.dataset_populator.new_history()
        hda1 = _dataset_to_param( self.dataset_populator.new_dataset( history_id, content='1\n2\n3' ) )
        inputs = {
            "file1": hda1,
            "numbering|_cwl__type_": "boolean",
            "numbering|_cwl__value_": True,
        }
        stdout = self._run_and_get_stdout( "cat1-tool", history_id, inputs, assert_ok=True )
        self.assertEquals(stdout, "     1\t1\n     2\t2\n     3\t3\n")

    @skip_without_tool( "cat1-tool" )
    def test_cat1_number_cwl_json( self ):
        """Test execution of cat1 using the "CWL" Galaxy job API representation."""
        history_id = self.dataset_populator.new_history()
        hda1 = _dataset_to_param( self.dataset_populator.new_dataset( history_id, content='1\n2\n3' ) )
        inputs = {
            "file1": hda1,
            "numbering": True,
        }
        stdout = self._run_and_get_stdout( "cat1-tool", history_id, inputs, assert_ok=True, inputs_representation="cwl" )
        self.assertEquals(stdout, "     1\t1\n     2\t2\n     3\t3\n")

    @skip_without_tool( "cat1-tool" )
    def test_cat1_number_cwl_json_file( self ):
        """Test execution of cat1 using the CWL job definition file."""
        run_object = self.dataset_populator.run_cwl_tool( "cat1-tool", "test/functional/tools/cwl_tools/draft3/cat-job.json")
        stdout = self._get_job_stdout( run_object.job_id )
        self.assertEquals(stdout, "Hello world!\n")

    @skip_without_tool( "cat1-tool" )
    def test_cat1_number_cwl_n_json_file( self ):
        run_object = self.dataset_populator.run_cwl_tool( "cat1-tool", "test/functional/tools/cwl_tools/draft3/cat-n-job.json")
        stdout = self._get_job_stdout( run_object.job_id )
        self.assertEquals(stdout, "     1\tHello world!\n")

    @skip_without_tool( "cat2-tool" )
    def test_cat2( self ):
        run_object = self.dataset_populator.run_cwl_tool( "cat2-tool", "test/functional/tools/cwl_tools/draft3/cat-job.json")
        stdout = self._get_job_stdout( run_object.job_id )
        self.assertEquals(stdout, "Hello world!\n")

    @skip_without_tool( "cat4-tool" )
    def test_cat4( self ):
        run_object = self.dataset_populator.run_cwl_tool( "cat4-tool", "test/functional/tools/cwl_tools/draft3/cat-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output1_content, "Hello world!\n")

    @skip_without_tool( "cat-default" )
    def test_cat_default( self ):
        run_object = self.dataset_populator.run_cwl_tool( "cat-default", job={})
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output1_content, "Hello world!\n")

    @skip_without_tool( "wc-tool" )
    def test_wc( self ):
        run_object = self.dataset_populator.run_cwl_tool( "wc-tool", "test/functional/tools/cwl_tools/draft3/wc-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        if not IS_OS_X:
            self.assertEquals(output1_content, "  16  198 1111\n")
        else:
            self.assertEquals(output1_content, "      16     198    1111\n")

    @skip_without_tool( "wc2-tool" )
    def test_wc2( self ):
        run_object = self.dataset_populator.run_cwl_tool( "wc2-tool", "test/functional/tools/cwl_tools/draft3/wc-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output1_content, "16")

    @skip_without_tool( "wc3-tool" )
    def test_wc3( self ):
        run_object = self.dataset_populator.run_cwl_tool(
            "wc4-tool",
            job={
                "file1": [
                    {
                        "class": "File",
                        "path": "whale.txt"
                    },
                ],
            },
            test_data_directory="test/functional/tools/cwl_tools/draft3/"
        )
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output1_content, "16")

    @skip_without_tool( "wc4-tool" )
    def test_wc4( self ):
        run_object = self.dataset_populator.run_cwl_tool( "wc4-tool", "test/functional/tools/cwl_tools/draft3/wc-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output1_content, "16")

    def _run_and_get_stdout( self, tool_id, history_id, inputs, **kwds):
        response = self._run( tool_id, history_id, inputs, **kwds )
        assert "jobs" in response
        job = response[ "jobs" ][ 0 ]
        job_id = job["id"]
        final_state = self.dataset_populator.wait_for_job( job_id )
        assert final_state == "ok"
        return self._get_job_stdout( job_id )

    def _get_job_stdout(self, job_id):
        job_details = self.dataset_populator.get_job_details( job_id, full=True )
        stdout = job_details.json()["stdout"]
        return stdout

    @skip_without_tool( "cat3-tool" )
    def test_cat3( self ):
        history_id = self.dataset_populator.new_history()
        hda1 = _dataset_to_param( self.dataset_populator.new_dataset( history_id, content='1\t2\t3' ) )
        inputs = {
            "f1": hda1,
        }
        response = self._run( "cat3-tool", history_id, inputs, assert_ok=True )
        output1 = response[ "outputs" ][ 0 ]
        output1_content = self.dataset_populator.get_history_dataset_content( history_id, dataset=output1 )
        assert output1_content == "1\t2\t3\n", output1_content

    @skip_without_tool( "sorttool" )
    def test_sorttool( self ):
        history_id = self.dataset_populator.new_history()
        hda1 = _dataset_to_param( self.dataset_populator.new_dataset( history_id, content='1\n2\n3' ) )
        inputs = {
            "reverse": False,
            "input": hda1
        }
        response = self._run( "sorttool", history_id, inputs, assert_ok=True )
        output1 = response[ "outputs" ][ 0 ]
        output1_content = self.dataset_populator.get_history_dataset_content( history_id, dataset=output1 )
        assert output1_content == "1\n2\n3\n", output1_content

    @skip_without_tool( "sorttool" )
    def test_sorttool_reverse( self ):
        history_id = self.dataset_populator.new_history()
        hda1 = _dataset_to_param( self.dataset_populator.new_dataset( history_id, content='1\n2\n3' ) )
        inputs = {
            "reverse": True,
            "input": hda1
        }
        response = self._run( "sorttool", history_id, inputs, assert_ok=True )
        output1 = response[ "outputs" ][ 0 ]
        output1_content = self.dataset_populator.get_history_dataset_content( history_id, dataset=output1 )
        assert output1_content == "3\n2\n1\n", output1_content

    @skip_without_tool( "env-tool1" )
    def test_env_tool1( self ):
        history_id = self.dataset_populator.new_history()
        inputs = {
            "in": "Hello World",
        }
        response = self._run( "env-tool1", history_id, inputs, assert_ok=True )
        output1 = response[ "outputs" ][ 0 ]
        output1_content = self.dataset_populator.get_history_dataset_content( history_id, dataset=output1 )
        self.assertEquals(output1_content, "Hello World\n")

    @skip_without_tool( "env-tool2" )
    def test_env_tool2( self ):
        run_object = self.dataset_populator.run_cwl_tool( "env-tool2", "test/functional/tools/cwl_tools/draft3/env-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output1_content, "hello test env\n")

    @skip_without_tool( "rename" )
    def test_rename( self ):
        run_object = self.dataset_populator.run_cwl_tool( "rename", "test/functional/tools/cwl_tools/draft3/rename-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output1_content, whale_text())

    @skip_without_tool( "optional-output" )
    def test_optional_output( self ):
        run_object = self.dataset_populator.run_cwl_tool( "optional-output", "test/functional/tools/cwl_tools/draft3/cat-job.json")
        output_file = run_object.output(0)
        optional_file = run_object.output(1)
        output_content = self.dataset_populator.get_history_dataset_content( run_object.history_id, dataset=output_file )
        optional_content = self.dataset_populator.get_history_dataset_content( run_object.history_id, dataset=optional_file )
        self.assertEquals(output_content, "Hello world!\n")
        self.assertEquals(optional_content, "null")

    @skip_without_tool( "optional-output2" )
    def test_optional_output2_on( self ):
        run_object = self.dataset_populator.run_cwl_tool(
            "optional-output2",
            job={
                "produce": "do_write",
            },
            test_data_directory="test/functional/tools/cwl_tools/draft3/"
        )
        output_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output_content, "bees\n")

    @skip_without_tool( "optional-output2" )
    def test_optional_output2_off( self ):
        run_object = self.dataset_populator.run_cwl_tool(
            "optional-output2",
            job={
                "produce": "dont_write",
            },
            test_data_directory="test/functional/tools/cwl_tools/draft3/"
        )
        output_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        self.assertEquals(output_content, "null")

    @skip_without_tool( "index1" )
    @skip_without_tool( "showindex1" )
    def test_index1( self ):
        run_object = self.dataset_populator.run_cwl_tool(
            "index1",
            job={
                "file": {
                    "class": "File",
                    "path": "whale.txt"
                },
            },
            test_data_directory="test/functional/tools/cwl_tools/draft3/",
        )
        output1 = self.dataset_populator.get_history_dataset_details( run_object.history_id )
        run_object = self.dataset_populator.run_cwl_tool(
            "showindex1",
            job={
                "file": {
                    "src": "hda",
                    "id": output1["id"],
                },
            },
            test_data_directory="test/functional/tools/cwl_tools/draft3/",
            history_id=run_object.history_id,
        )
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        assert "call: 1\n" in output1_content, output1_content

    @skip_without_tool( "any1" )
    def test_any1_0( self ):
        run_object = self.dataset_populator.run_cwl_tool(
            "any1",
            job={"bar": 7},
            test_data_directory="test/functional/tools/cwl_tools/draft3/",
        )
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        assert output1_content == '7', output1_content

    @skip_without_tool( "any1" )
    def test_any1_1( self ):
        run_object = self.dataset_populator.run_cwl_tool(
            "any1",
            job={"bar": "7"},
            test_data_directory="test/functional/tools/cwl_tools/draft3/",
        )
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        assert output1_content == '"7"', output1_content

    @skip_without_tool( "any1" )
    def test_any1_2( self ):
        run_object = self.dataset_populator.run_cwl_tool(
            "any1",
            job={"bar": {"Cow": ["Turkey"]}},
            test_data_directory="test/functional/tools/cwl_tools/draft3/",
        )
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        assert output1_content == '{"Cow": ["Turkey"]}', output1_content

    @skip_without_tool( "null-expression1-tool" )
    def test_null_expression_1_1( self ):
        run_object = self.dataset_populator.run_cwl_tool( "null-expression1-tool", "test/functional/tools/cwl_tools/draft3/empty.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        assert output1_content == '1', output1_content

    @skip_without_tool( "null-expression1-tool" )
    def test_null_expression_1_2( self ):
        run_object = self.dataset_populator.run_cwl_tool( "null-expression1-tool", "test/functional/tools/cwl_tools/draft3/null-expression2-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        assert output1_content == '2', output1_content

    @skip_without_tool( "null-expression2-tool" )
    def test_null_expression_any_bad_1( self ):
        """Test explicitly passing null to Any type without a default value fails."""
        run_object = self.dataset_populator.run_cwl_tool( "null-expression2-tool", "test/functional/tools/cwl_tools/draft3/null-expression1-job.json", assert_ok=False)
        self._assert_status_code_is( run_object.run_response, 400 )

    @skip_without_tool( "null-expression2-tool" )
    def test_null_expression_any_bad_2( self ):
        """Test Any without defaults can be unspecified."""
        run_object = self.dataset_populator.run_cwl_tool( "null-expression2-tool", "test/functional/tools/cwl_tools/draft3/empty.json", assert_ok=False)
        self._assert_status_code_is( run_object.run_response, 400 )

    @skip_without_tool( "params" )
    def test_params1( self ):
        run_object = self.dataset_populator.run_cwl_tool( "params", "test/functional/tools/cwl_tools/draft3/empty.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id )
        assert output1_content == '"b b"', output1_content

    @skip_without_tool( "parseInt-tool" )
    def test_parse_int_tool( self ):
        run_object = self.dataset_populator.run_cwl_tool( "parseInt-tool", "test/functional/tools/cwl_tools/draft3/parseInt-job.json")
        output1_content = self.dataset_populator.get_history_dataset_content( run_object.history_id, hid=2 )
        self.assertEquals(output1_content, '42')
        output1 = self.dataset_populator.get_history_dataset_details( run_object.history_id, hid=2 )
        self.assertEquals(output1["extension"], "expression.json")

    # def test_dynamic_tool_execution( self ):
    #     workflow_tool_json = {
    #         'inputs': [{'inputBinding': {}, 'type': 'File', 'id': 'file:///home/john/workspace/galaxy/test/unit/tools/cwl_tools/draft3/count-lines2-wf.cwl#step1/wc/wc_file1'}],
    #         'stdout': 'output.txt',
    #         'id': 'file:///home/john/workspace/galaxy/test/unit/tools/cwl_tools/draft3/count-lines2-wf.cwl#step1/wc',
    #         'outputs': [{'outputBinding': {'glob': 'output.txt'}, 'type': 'File', 'id': 'file:///home/john/workspace/galaxy/test/unit/tools/cwl_tools/draft3/count-lines2-wf.cwl#step1/wc/wc_output'}],
    #         'baseCommand': 'wc',
    #         'class': 'CommandLineTool'
    #     }

    #     create_payload = dict(
    #         representation=json.dumps(workflow_tool_json),
    #     )
    #     create_response = self._post( "dynamic_tools", data=create_payload, admin=True )
    #     self._assert_status_code_is( create_response, 200 )

    # TODO: Use mixin so this can be shared with tools test case.
    def _run( self, tool_id, history_id, inputs, assert_ok=False, tool_version=None, inputs_representation=None ):
        payload = self.dataset_populator.run_tool_payload(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
            inputs_representation=inputs_representation,
        )
        if tool_version is not None:
            payload[ "tool_version" ] = tool_version
        create_response = self._post( "tools", data=payload )
        if assert_ok:
            self._assert_status_code_is( create_response, 200 )
            create = create_response.json()
            self._assert_has_keys( create, 'outputs' )
            return create
        else:
            return create_response


def whale_text():
    return open("test/functional/tools/cwl_tools/draft3/whale.txt", "r").read()


def _dataset_to_param( dataset ):
    return dict(
        src='hda',
        id=dataset[ 'id' ]
    )
