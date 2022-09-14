import logging
from functools import wraps

from galaxy.web.framework import url_for

log = logging.getLogger(__name__)


def require_login(verb="perform this action", use_panels=False):
    def argcatcher(func):
        @wraps(func)
        def decorator(self, trans, *args, **kwargs):
            if trans.get_user():
                return func(self, trans, *args, **kwargs)
            else:
                return trans.show_error_message(
                    'You must be <a target="galaxy_main" href="%s">logged in</a> to %s.'
                    % (url_for(controller="user", action="login"), verb),
                    use_panels=use_panels,
                )

        return decorator

    return argcatcher
