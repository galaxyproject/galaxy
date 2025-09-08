import os
from typing import (
    Any,
    Dict,
    Optional,
)

from webob.compat import cgi_FieldStorage

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesAppContext
from galaxy.schema.schema import GenerateTourResponse
from galaxy.structured_app import StructuredApp
from galaxy.tools import Tool
from galaxy.tools.parameters.grouping import Conditional
from galaxy.tours import (
    TourDetails,
    TourStep,
)
from galaxy.util import Params


class ToursManager:
    def __init__(self, app: StructuredApp):
        self._app = app

    def generate_tour(self, tool_id: str, tool_version: str, trans: ProvidesAppContext) -> GenerateTourResponse:
        """
        Generate a tour designed for the given tool.

        :param  tool_id:       The tool ID to generate a tour for
        :type   tool_id:       str
        :param  tool_version:  The version of the tool
        :type   tool_version:  str
        :returns:             An object containing the tour and any uploaded dataset hids (if applicable)
        :rtype:               dict
        """
        if not tool_id:
            raise RequestParameterInvalidException("Tool id is missing.")
        if not tool_version:
            raise RequestParameterInvalidException("Tool version is missing.")

        tour_generator = TourGenerator(trans, tool_id, tool_version)
        return tour_generator.get_data()


class TourGenerator:
    def __init__(self, trans: ProvidesAppContext, tool_id: str, tool_version: str) -> None:
        self._trans = trans
        self._tool: Tool = self._get_and_ensure_tool(tool_id, tool_version)
        self._use_datasets = True
        self._data_inputs: Dict[str, Any] = {}
        self._tour: Optional[TourDetails] = None
        self._hids: Dict[str, Any] = {}
        self._upload_test_data()
        self._generate_tour()

    def _get_and_ensure_tool(self, tool_id: str, tool_version: Optional[str]) -> Tool:
        """Get the tool and ensure it exists."""
        tool = self._trans.app.toolbox.get_tool(tool_id, tool_version)
        if not tool:
            raise ObjectNotFound(f'Tool "{tool_id}" version "{tool_version}" does not exist.')
        return tool

    def _upload_test_data(self):
        """
        Upload test datasets, which are defined in the <test></test>
        section of the provided tool.
        """
        if not self._tool.tests:
            raise RequestParameterInvalidException("Tests are not defined.")
        self._test = self._tool.tests[0]
        # All inputs with the type 'data'
        self._data_inputs = {x.name: x for x in self._tool.input_params if x.type == "data"}
        # Datasets from the <test></test> section
        test_datasets = {
            input_name: self._test.inputs[input_name][0]
            for input_name in self._data_inputs.keys()
            if input_name in self._test.inputs.keys()
        }
        # Conditional datasets
        for name in self._test.inputs.keys():
            if "|" in name:
                input_name = name.split("|")[1]
                if input_name in self._data_inputs.keys():
                    test_datasets.update({input_name: self._test.inputs[name][0]})
        if not test_datasets.keys():
            not_supported_input_types = [
                k for k, v in self._tool.inputs.items() if v.type == "repeat" or v.type == "data_collection"
            ]
            if not_supported_input_types:
                raise RequestParameterInvalidException("Not supported input types.")
            else:
                # Some tests don't have data inputs at all,
                # so we can generate a tour without them
                self._use_datasets = False
                return
        # Upload all test datasets
        for input_name, input in self._data_inputs.items():
            if input_name in test_datasets.keys():
                filename = test_datasets[input_name]
                input_path = self._tool.test_data_path(filename)
                if not input_path:
                    raise ObjectNotFound(f'Test dataset "{input_name}" doesn\'t exist.')
                upload_tool: Tool = self._get_and_ensure_tool("upload1", None)
                filename = os.path.basename(input_path)
                with open(input_path, "rb") as f:
                    content = f.read()
                    headers = {
                        "content-disposition": 'form-data; name="{}"; filename="{}"'.format(
                            "files_0|file_data", filename
                        ),
                    }
                    input_file = cgi_FieldStorage(headers=headers)
                    input_file.file = input_file.make_file()
                    input_file.file.write(content)
                    inputs = {
                        "dbkey": "?",  # is it always a question mark?
                        "file_type": input.extensions[0],
                        "files_0|type": "upload_dataset",
                        "files_0|space_to_tab": None,
                        "files_0|to_posix_lines": "Yes",
                        "files_0|file_data": input_file,
                    }
                    params = Params(inputs, sanitize=False)
                    incoming = params.__dict__
                    output = upload_tool.handle_input(self._trans, incoming, history=None)
                    job_errors = output.get("job_errors", [])
                    if job_errors:
                        raise RequestParameterInvalidException("Cannot upload a dataset.")
                    else:
                        self._hids.update({input_name: output["out_data"][0][1].hid})

    def _generate_tour(self):
        """Generate a tour."""
        tour_name = f"{self._tool.name} Tour"
        test_inputs = self._test.inputs.keys()
        steps: list[TourStep] = [
            TourStep(
                title=tour_name,
                content=f"This short tour will guide you through the <b>{self._tool.name}</b> tool.",
                orphan=True,
            )
        ]
        for name, input in self._tool.inputs.items():
            cond_case_steps: list[TourStep] = []
            if input.type == "repeat":
                continue
            step: TourStep = TourStep(
                title=getattr(input, "label", name),
                element=f"[id='form-element-{name}']",
                placement="right",
                content="",
            )
            if input.type == "text":
                if name in test_inputs:
                    param = self._test.inputs[name]
                    step.content = f"Enter value(s): <b>{param}</b>"
                else:
                    step.content = "Enter a value"
            elif input.type == "integer" or input.type == "float":
                if name in test_inputs:
                    num_param = self._test.inputs[name][0]
                    step.content = f"Enter number: <b>{num_param}</b>"
                else:
                    step.content = "Enter a number"
            elif input.type == "boolean":
                if name in test_inputs:
                    choice = "Yes" if self._test.inputs[name][0] is True else "No"
                    step.content = f"Choose <b>{choice}</b>"
                else:
                    step.content = "Choose Yes/No"
            elif input.type == "select":
                params = []
                if name in test_inputs:
                    for option in getattr(input, "static_options", []):
                        for test_option in self._test.inputs[name]:
                            if test_option == option[1]:
                                params.append(option[0])
                if params:
                    select_param = ", ".join(params)
                    step.content = f"Select parameter(s): <b>{select_param}</b>"
                else:
                    step.content = "Select a parameter"
            elif input.type == "data":
                if name in test_inputs:
                    hid = self._hids[name]
                    dataset = self._test.inputs[name][0]
                    step.content = f"Select dataset: <b>{hid}: {dataset}</b>"
                else:
                    step.content = "Select a dataset"
            elif input.type == "conditional" and isinstance(input, Conditional):
                test_param = input.test_param
                if test_param is None:
                    param_id = f"{input.name}|"
                    step.title = input.label
                else:
                    param_id = f"{input.name}|{test_param.name}"
                    step.title = test_param.label

                step.element = f"[id='form-element-{param_id}']"
                step.element = f"[id='form-element-{param_id}']"
                params = []
                if param_id in self._test.inputs.keys():
                    if test_param is not None and hasattr(test_param, "static_options"):
                        for option in test_param.static_options:
                            for test_option in self._test.inputs[param_id]:
                                if test_option == option[1]:
                                    params.append(option[0])
                    # Conditional param cases
                    cases: Dict[str, str] = {}
                    for case in input.cases:
                        if case.inputs is not None:
                            for key, value in case.inputs.items():
                                if key not in cases.keys():
                                    cases[key] = value.label
                    for case_id, case_title in cases.items():
                        tour_id = f"{input.name}|{case_id}"
                        if tour_id in self._test.inputs.keys():
                            if case_id in self._data_inputs.keys():
                                hid = self._hids[case_id]
                                dataset = self._test.inputs[tour_id][0]
                                step_msg = f"Select dataset: <b>{hid}: {dataset}</b>"
                            else:
                                case_params = ", ".join(self._test.inputs[tour_id])
                                step_msg = f"Select parameter(s): <b>{case_params}</b>"
                            cond_case_steps.append(
                                TourStep(
                                    title=case_title,
                                    element=f"[id='form-element-{tour_id}']",
                                    placement="right",
                                    content=step_msg,
                                )
                            )
                if params:
                    cond_param = ", ".join(params)
                    step.content = f"Select parameter(s): <b>{cond_param}</b>"
                else:
                    step.content = "Select a parameter"
            elif input.type == "data_column":
                if name in test_inputs:
                    column_param = self._test.inputs[name][0]
                    step.content = f"Select <b>Column: {column_param}</b>"
                else:
                    step.content = "Select a column"
            else:
                step.content = "Select a parameter"
            steps.append(step)
            if cond_case_steps:
                steps.extend(cond_case_steps)  # add conditional input steps

        # Add the last step
        steps.append(
            TourStep(
                title="Execute tool",
                content="Click <b>Execute</b> button to run the tool.",
                element="#execute",
                placement="bottom",
            )
        )

        description = f"This tour describes how to run the {self._tool.name} tool."

        self._tour = TourDetails(
            title_default=tour_name,
            name=tour_name,
            description=description,
            tags=[],
            # TODO: Adding the `new_history` requirement would make sense but it doesn't make sense
            #       if we've already uploaded datasets. Find a way to create a history and set it
            #       to current first?
            requirements=[],
            steps=steps,
        )

    def get_data(self) -> GenerateTourResponse:
        """
        Return a dictionary with the uploaded datasets' history ids and
        the generated tour.
        """
        return GenerateTourResponse(
            use_datasets=self._use_datasets,
            uploaded_hids=list(self._hids.values()),
            tour=self._tour,
        )
