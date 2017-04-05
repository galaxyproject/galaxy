import os
import logging
from cgi import FieldStorage

from galaxy.util import Params

log = logging.getLogger(__name__)


def upload_test_data(trans, tests):
    result = {'errors': []}

    if tests is None:
        raise ValueError('Tests are not defined.')

    test = tests[0]
    inputs = test.inputs['input']

    if not any(inputs):
        raise ValueError('Test data is missing.')

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

    # TODO:me: return job_id

    return result


def generate_tour(tool):
    tour_name = tool.name + ' Tour'

    steps = [{
        'title': tour_name,
        'content': 'This short tour will guide you through the <b>' +
                   tool.name + '</b> tool.',
        'orphan': True
    }]

    for name, input in tool.inputs.items():
        step = {
            'title': input.label,
            'element': '[tour_id=%s]' % name,
            'placement': 'right',
        }

        if input.type == 'text':
            step['content'] = 'Enter parameter <b>%s</b>.' % input.label
        elif input.type == 'data':
            step['content'] = 'Select dataset.'
        else:
            step['content'] = 'Select parameter <b>%s</b>.' % input.label,

        steps.append(step)

    # Add last step
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

        # Generate Tour
        data = generate_tour(tool)

        # tests = tool.tests
        # upload_result = upload_test_data(trans, tests)
        # if upload_result['errors']:
        #     raise ValueError(str(upload_result['errors']))

    except Exception as e:
        error = str(e)
        log.exception(e)

    return {'success': not error, 'error': error, 'data': data}
