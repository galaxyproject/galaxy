import logging

from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController
from galaxy.util import docstring_trim

log = logging.getLogger(__name__)


def get_dynamic_post_processing_actions(config_post_actions):
    """ Extract information about all post processing actions from the galaxy.ini config file. """
    actions = list()
    for action_name in config_post_actions:
        if ":" in action_name:
            # Should be a submodule of actions (e.g. examples:microscope_control)
            (module_name, class_name) = action_name.rsplit(":", 1)
            module_name = 'galaxy.jobs.actions.dynamic.%s' % module_name.strip()
            module = __import__(module_name, globals(),
                                fromlist=['temp_module'])
            class_object = getattr(module, class_name.strip())

            print(class_object, module)

        else:
            # No module found it has to be explicitly imported.
            module = __import__('galaxy.jobs.actions.dynamic',
                                globals(), fromlist=['temp_module'])
            class_object = getattr(globals(), action_name.strip())

        doc_string = docstring_trim(class_object.__doc__)
        split = doc_string.split('\n\n')
        if split:
            sdesc = split[0].strip()
        else:
            log.error(
                'No description specified in the __doc__ string for %s.' % action_name)
        if len(split) > 1:
            description = split[1].strip()
        else:
            description = ''

        actions.append(dict(actionpath=action_name,
                            short_desc=sdesc, desc=description, cl=class_object))
    return actions


class DynamicActionsController(BaseAPIController):
    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/dynamic_actions
        Return a list containing dynamic actions.
        """
        dynamic_actions = get_dynamic_post_processing_actions(
            trans.app.config.dynamic_post_processing_actions)

        # Only actions with the correct privileges should be shown
        dynamic_actions_filtered = []
        for dynamic_action in dynamic_actions:
            action_class = dynamic_action['cl'](trans=trans)
            if action_class.check_privileges():
                dynamic_actions_filtered.append(dynamic_action)

        return list(map(lambda x: {
            'name': x['short_desc'],
            'value': x['actionpath'].replace(':', '-'),
        }, dynamic_actions_filtered))
