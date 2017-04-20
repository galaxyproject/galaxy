import os
import logging
from cgi import FieldStorage

from galaxy.util import Params

log = logging.getLogger(__name__)


class TourGenerator(object):
    def __init__(self, trans, tool_id):
        self._trans = trans
        self._tool = self._trans.app.toolbox.get_tool(tool_id)

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
            raise ValueError('Tests are not defined.')

        self._test = self._tool.tests[0]
        input_keys = [k for k, v in self._tool.inputs.data.items() if
                      v.type == 'data']
        input_datasets = [
            self._test.inputs[input_key]
            for input_key in input_keys
        ]

        if not input_datasets:
            raise ValueError('Test data is missing.')

        # Upload all test datasets
        for i, input in enumerate(input_datasets):
            input_name = input[0]
            input_path = os.path.abspath(os.path.join('test-data', input_name))

            if not os.path.exists(input_path):
                raise ValueError(
                    'Test dataset "%s" doesn\'t exist.' % input_name)

            upload_tool = self._trans.app.toolbox.get_tool('upload1')
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
                output = upload_tool.handle_input(self._trans, incoming,
                                                  history=None)

                job_errors = output.get('job_errors', [])
                if job_errors:
                    # self._errors.extend(job_errors)
                    raise ValueError('Cannot upload a dataset.')
                else:
                    self._hids.update({
                        input_keys[i]: output['out_data'][0][1].hid
                    })

    def _generate_tour(self):
        """ Generate a tour. """
        tour_name = self._tool.name + ' Tour'

        steps = [{
            'title': tour_name,
            'content': 'This short tour will guide you through the <b>' +
                       self._tool.name + '</b> tool.',
            'orphan': True
        }]

        # TODO@me: for ... in test.inputs?
        for name, input in self._tool.inputs.items():
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
                text_param = self._test.inputs[name]
                step['content'] = 'Enter parameter(s): <b>%s</b>' % text_param

            elif input.type == 'integer':
                integer_param = self._test.inputs[name][0]
                step['content'] = 'Enter parameter: <b>%s</b>' % integer_param

            elif input.type == 'boolean':
                choice = 'Yes' if self._test.inputs[name][0] is True else 'No'
                step['content'] = 'Choose <b>%s</b>' % choice

            elif input.type == 'select':
                select_param = input.label
                params = []
                for option in self._tool.inputs[name].static_options:
                    if name in self._test.inputs.keys():
                        for test_option in self._test.inputs[name]:
                            if test_option == option[1]:
                                params.append(option[0])
                if params:
                    select_param = ', '.join(params)
                step[
                    'content'] = 'Select parameter(s): <b>%s</b>' % \
                                 select_param

            elif input.type == 'data':
                hid = self._hids[name]
                dataset = self._test.inputs[name][0]
                step['content'] = 'Select dataset <b>%s: %s</b>' % (
                    hid, dataset
                )

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

        self._tour = {
            'title_default': tour_name,
            'name': tour_name,
            'description': self._tool.name + ' ' + self._tool.description,
            'steps': steps
        }

    def get_data(self):
        """ 
        Return a dictionary with the uploaded datasets' history ids and
        the generated tour.
        """
        return {'hids': list(self._hids.values()), 'tour': self._tour}


def main(trans, webhook, params):
    error = ''
    data = {}

    try:
        if not params or 'tool_id' not in params.keys():
            raise KeyError('Tool id is missing.')

        tool_id = params['tool_id']
        tour_generator = TourGenerator(trans, tool_id)
        data = tour_generator.get_data()

    except Exception as e:
        error = str(e)
        log.exception(e)

    return {'success': not error, 'error': error, 'data': data}
