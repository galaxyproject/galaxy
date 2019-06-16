from galaxy.tools.deps.mulled.get_tests import get_commands_from_yaml
from galaxy.util import smart_str


TEST_RECIPE = r"""
{% set name = "eagle" %}
package:
  name: '{{ name }}'
requirements:
  run:
    - python
    - flask
test:
  imports:
    - eagle
  commands:
    - eagle --help
"""


def test_get_commands_from_yaml():
    commands = get_commands_from_yaml(smart_str(TEST_RECIPE))
    assert commands['imports'] == ['eagle']
    assert commands['commands'] == ['eagle --help']
    assert commands['import_lang'] == 'python -c'
