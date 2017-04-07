import os
import logging
from cgi import FieldStorage

from galaxy.util import Params

log = logging.getLogger(__name__)


def upload_test_data(trans, tests):
    result = {'errors': []}

    if not tests:
        raise ValueError('Tests are not defined.')

    test = tests[0]

    # TODO@me: deal with two datasets
    inputs = []
    for input_key in ['input', 'input1', 'input_file', 'input_file1']:
        if input_key in test.inputs.keys():
            inputs = test.inputs[input_key]
            break

    if not inputs:
        raise ValueError('Test data is missing.')

    if type(inputs) is not list:
        raise ValueError('Test data type is unsuitable.')

    input_name = inputs[0]
    input_path = os.path.abspath(os.path.join('test-data', input_name))

    if not os.path.exists(input_path):
        raise ValueError('Test data doesn\'t exist.')

    upload_tool = trans.app.toolbox.get_tool('upload1')
    filename = os.path.basename(input_path)

    with open(input_path, 'r') as f:
        content = f.read()
        headers = {
            'content-disposition':
                'form-data; name="{}"; filename="{}"'.format(
                    'files_0|file_data', filename
                ),
        }

        input_file = FieldStorage(headers=headers)
        input_file.file = input_file.make_file()
        input_file.file.write(content)

        inputs = {
            'dbkey': '?',  # is it always a question mark?
            'file_type': 'auto',
            'files_0|type': 'upload_dataset',
            'files_0|space_to_tab': None,
            'files_0|to_posix_lines': 'Yes',
            'files_0|file_data': input_file,
        }

        params = Params(inputs, sanitize=False)
        incoming = params.__dict__
        vars = upload_tool.handle_input(trans, incoming, history=None)

        job_errors = vars.get('job_errors', [])
        if job_errors:
            result['errors'] = job_errors

    return result


def generate_tour(tool):
    tour_name = tool.name + ' Tour'
    test = tool.tests[0]

    steps = [{
        'title': tour_name,
        'content': 'This short tour will guide you through the <b>' +
                   tool.name + '</b> tool.',
        'orphan': True
    }]

    # TODO@me: for ... in test.inputs?
    for name, input in tool.inputs.items():
        # Skip this type as Tours Framework doesn't add tour_id to the
        # corresponding DOM element
        if input.type == 'repeat':
            continue

        step = {
            'title': input.label,
            'element': '[tour_id=%s]' % name,
            'placement': 'right',
            'content': ''
        }

        if input.type == 'text':
            text_param = test.inputs[name]
            step['content'] = 'Enter parameter(s): <b>%s</b>' % text_param

        elif input.type == 'integer':
            integer_param = test.inputs[name][0]
            step['content'] = 'Enter parameter: <b>%s</b>' % integer_param

        elif input.type == 'boolean':
            choice = 'Yes' if test.inputs[name][0] is True else 'No'
            step['content'] = 'Choose <b>%s</b>' % choice

        elif input.type == 'select':
            select_param = input.label
            params = []
            for option in tool.inputs[name].static_options:
                if name in test.inputs.keys():
                    for test_option in test.inputs[name]:
                        if test_option == option[1]:
                            params.append(option[0])
            if params:
                select_param = ', '.join(params)
            step['content'] = 'Select parameter(s): <b>%s</b>' % select_param

        elif input.type == 'data':
            dataset = test.inputs[name][0]
            step['content'] = 'Select dataset <b>%s</b>' % dataset

        # elif input.type == 'repeat':
        #     step['title'] = input.title
        #     step['content'] = 'Select parameter <b>%s</b>' % input.title

        elif input.type == 'conditional':
            # TODO@me: deal with this input type
            pass

        else:
            step['content'] = 'Select parameter <b>%s</b>' % input.label

        steps.append(step)

    # Add the last step
    steps.append({
        'title': 'Execute tool',
        'content': 'Click <b>Execute</b> button to run the tool.',
        'element': '#execute',
        'placement': 'bottom',
        # 'postclick': ['#execute']
    })

    return {
        'title_default': tour_name,
        'name': tour_name,
        'description': tool.name + ' ' + tool.description,
        'steps': steps
    }


def main(trans, webhook, params):
    error = ''
    data = {}

    try:
        if not params or 'tool_id' not in params.keys():
            raise KeyError('Tool id is missing.')

        tool_id = params['tool_id']
        tool = trans.app.toolbox.get_tool(tool_id)

        tests = tool.tests
        upload_result = upload_test_data(trans, tests)
        if upload_result['errors']:
            raise ValueError(str(upload_result['errors']))

        # Generate Tour
        data = generate_tour(tool)

    except Exception as e:
        error = str(e)
        log.exception(e)

    return {'success': not error, 'error': error, 'data': data}
