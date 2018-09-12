from galaxy.jobs.actions.post import get_dynamic_post_processing_actions
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController


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
