import logging
import os

from webob.compat import cgi_FieldStorage

from galaxy.util import Params

log = logging.getLogger(__name__)


class TourGenerator:
    def __init__(self, trans, tool_id, tool_version):
        self._trans = trans
        self._tool = self._trans.app.toolbox.get_tool(tool_id, tool_version)
        self._use_datasets = True
        self._data_inputs = {}
        self._tour = {}
        self._hids = {}
        self._errors = []
        self._upload_test_data()
        self._generate_tour()

    def _upload_test_data(self):
        """
        Upload test datasets, which are defined in the <test></test>
        section of the provided tool.
        """
        if not self._tool.tests:
            raise ValueError("Tests are not defined.")
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
                raise ValueError("Not supported input types.")
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
                    raise ValueError('Test dataset "%s" doesn\'t exist.' % input_name)
                upload_tool = self._trans.app.toolbox.get_tool("upload1")
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
                        # self._errors.extend(job_errors)
                        raise ValueError("Cannot upload a dataset.")
                    else:
                        self._hids.update({input_name: output["out_data"][0][1].hid})

    def _generate_tour(self):
        """Generate a tour."""
        tour_name = self._tool.name + " Tour"
        test_inputs = self._test.inputs.keys()
        steps = [
            {
                "title": tour_name,
                "content": "This short tour will guide you through the <b>" + self._tool.name + "</b> tool.",
                "orphan": True,
            }
        ]
        for name, input in self._tool.inputs.items():
            cond_case_steps = []
            if input.type == "repeat":
                continue
            step = {
                "title": input.label,
                "element": "[id='form-element-%s']" % name,
                "placement": "right",
                "content": "",
            }
            if input.type == "text":
                if name in test_inputs:
                    param = self._test.inputs[name]
                    step["content"] = "Enter value(s): <b>%s</b>" % param
                else:
                    step["content"] = "Enter a value"
            elif input.type == "integer" or input.type == "float":
                if name in test_inputs:
                    num_param = self._test.inputs[name][0]
                    step["content"] = "Enter number: <b>%s</b>" % num_param
                else:
                    step["content"] = "Enter a number"
            elif input.type == "boolean":
                if name in test_inputs:
                    choice = "Yes" if self._test.inputs[name][0] is True else "No"
                    step["content"] = "Choose <b>%s</b>" % choice
                else:
                    step["content"] = "Choose Yes/No"
            elif input.type == "select":
                params = []
                if name in test_inputs:
                    for option in input.static_options:
                        for test_option in self._test.inputs[name]:
                            if test_option == option[1]:
                                params.append(option[0])
                if params:
                    select_param = ", ".join(params)
                    step["content"] = "Select parameter(s): <b>%s</b>" % select_param
                else:
                    step["content"] = "Select a parameter"
            elif input.type == "data":
                if name in test_inputs:
                    hid = self._hids[name]
                    dataset = self._test.inputs[name][0]
                    step["content"] = f"Select dataset: <b>{hid}: {dataset}</b>"
                else:
                    step["content"] = "Select a dataset"
            elif input.type == "conditional":
                param_id = f"{input.name}|{input.test_param.name}"
                step["title"] = input.test_param.label
                step["element"] = "[id='form-element-%s']" % param_id
                params = []
                if param_id in self._test.inputs.keys():
                    for option in input.test_param.static_options:
                        for test_option in self._test.inputs[param_id]:
                            if test_option == option[1]:
                                params.append(option[0])
                    # Conditional param cases
                    cases = {}
                    for case in input.cases:
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
                                step_msg = "Select parameter(s): " + "<b>%s</b>" % case_params
                            cond_case_steps.append(
                                {
                                    "title": case_title,
                                    "element": "[id='form-element-%s']" % tour_id,
                                    "placement": "right",
                                    "content": step_msg,
                                }
                            )
                if params:
                    cond_param = ", ".join(params)
                    step["content"] = "Select parameter(s): <b>%s</b>" % cond_param
                else:
                    step["content"] = "Select a parameter"
            elif input.type == "data_column":
                if name in test_inputs:
                    column_param = self._test.inputs[name][0]
                    step["content"] = "Select <b>Column: %s</b>" % column_param
                else:
                    step["content"] = "Select a column"
            else:
                step["content"] = "Select a parameter"
            steps.append(step)
            if cond_case_steps:
                steps.extend(cond_case_steps)  # add conditional input steps
        # Add the last step
        steps.append(
            {
                "title": "Execute tool",
                "content": "Click <b>Execute</b> button to run the tool.",
                "element": "#execute",
                "placement": "bottom",
            }
        )
        self._tour = {
            "title_default": tour_name,
            "name": tour_name,
            "description": self._tool.name + " " + self._tool.description,
            "steps": steps,
        }

    def get_data(self):
        """
        Return a dictionary with the uploaded datasets' history ids and
        the generated tour.
        """
        return {"useDatasets": self._use_datasets, "hids": list(self._hids.values()), "tour": self._tour}


def main(trans, webhook, params):
    error = ""
    data = {}
    try:
        if not params or "tool_id" not in params.keys():
            raise KeyError("Tool id is missing.")
        if not params or "tool_version" not in params.keys():
            raise KeyError("Tool version is missing.")
        tool_id = params["tool_id"]
        tool_version = params["tool_version"]
        tour_generator = TourGenerator(trans, tool_id, tool_version)
        data = tour_generator.get_data()
    except Exception as e:
        error = str(e)
        log.exception(e)
    return {"success": not error, "error": error, "data": data}
