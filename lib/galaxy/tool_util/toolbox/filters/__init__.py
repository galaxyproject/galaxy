class FilterFactory:
    """
    An instance of this class is responsible for filtering the list
    of tools presented to a given user in a given context.
    """

    def __init__(self, toolbox):
        pass

    def build_filters(self, trans, **kwds):
        """
        Build list of filters to check tools against given current context.
        """
        return {"tool": [_not_hidden, _handle_authorization], "section": [], "label": []}


# Stock Filter Functions
def _not_hidden(context, tool):
    return not tool.hidden


def _handle_authorization(context, tool):
    user = context.trans.user
    if tool.require_login and not user:
        return False
    if not tool.allow_user_access(user, attempting_access=False):
        return False
    return True
