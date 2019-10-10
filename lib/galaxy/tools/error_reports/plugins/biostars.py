"""The module describes the ``biostars`` error plugin."""
from __future__ import absolute_import

import logging

from galaxy.util import biostar
from galaxy.util import string_as_bool
from galaxy.web.base.controller import url_for
from . import ErrorPlugin

log = logging.getLogger(__name__)


class BiostarsPlugin(ErrorPlugin):
    """Send error report as an issue on Biostars
    """
    plugin_type = "biostars"

    def __init__(self, **kwargs):
        self.app = kwargs['app']
        self.verbose = string_as_bool(kwargs.get('verbose', True))
        self.user_submission = string_as_bool(kwargs.get('user_submission', True))

    def submit_report(self, dataset, job, tool, **kwargs):
        """Doesn't do anything, just shows a link to submit on biostars.
        """
        # This class specifically does nothing special for compliance purposes
        # because the user is willingly posting their data on a public
        # first/third-party site. Maybe should do something about the dialog
        # linking to the biostars privacy policy during the "submit to
        # biostars" dialog?

        try:
            assert biostar.biostar_enabled(self.app), ValueError("Biostar is not configured for this galaxy instance")
            assert self.app.config.biostar_enable_bug_reports, ValueError("Biostar is not configured to allow bug reporting for this galaxy instance")
            print(kwargs)

            url = url_for(controller='biostar',
                          action='biostar_tool_bug_report',
                          hda=self.app.security.encode_id(dataset.id),
                          email=kwargs['email'], message=kwargs['message'])
            return ('Click <a href="%s">here</a> to submit to BioStars' % url, 'success')
        except Exception as e:
            return ("An error occurred submitting the report to biostars: %s" % str(e), "danger")


__all__ = ('BiostarsPlugin', )
