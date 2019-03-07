"""
Controller for integration with the Biostar application
"""
from galaxy.util import biostar
from galaxy.web.base.controller import (
    BaseUIController,
    error,
    web
)


class BiostarController(BaseUIController):
    """
    Provides integration with Biostar through external authentication, see: http://liondb.com/help/x/
    """

    @web.expose
    def biostar_redirect(self, trans, payload=None, biostar_action=None):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and optional information about a specific tool.
        """
        try:
            url, payload = biostar.get_biostar_url(trans.app, payload=payload, biostar_action=biostar_action)
        except Exception as e:
            return error(str(e))
        # Only create/log in biostar user if is registered Galaxy user
        if trans.user:
            biostar.create_cookie(trans, trans.app.config.biostar_key_name, trans.app.config.biostar_key, trans.user.email)
        if payload:
            return trans.fill_template("biostar/post_redirect.mako", post_url=url, form_inputs=payload)
        return trans.response.send_redirect(url)

    @web.expose
    def biostar_tool_tag_redirect(self, trans, tool_id=None):
        """
        Generate a redirect to a Biostar site using tag for tool.
        """
        # tool_id is required
        if tool_id is None:
            return error("No tool_id provided")
        # Load the tool
        tool_version_select_field, tools, tool = \
            self.app.toolbox.get_tool_components(tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=True)
        # No matching tool, unlikely
        if not tool:
            return error("No tool found matching '%s'" % tool_id)
        # Tool specific information for payload
        payload = biostar.populate_tag_payload(tool=tool)
        # Pass on to standard redirect method
        return self.biostar_redirect(trans, payload=payload, biostar_action='show_tags')

    @web.expose
    def biostar_question_redirect(self, trans, payload=None):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool.
        """
        # Pass on to standard redirect method
        return self.biostar_redirect(trans, payload=payload, biostar_action='new_post')

    @web.expose
    def biostar_tool_question_redirect(self, trans, tool_id=None):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool.
        """
        # tool_id is required
        if tool_id is None:
            return error("No tool_id provided")
        # Load the tool
        tool_version_select_field, tools, tool = \
            self.app.toolbox.get_tool_components(tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=True)
        # No matching tool, unlikely
        if not tool:
            return error("No tool found matching '%s'" % tool_id)
        # Tool specific information for payload
        payload = biostar.populate_tool_payload(tool=tool)
        # Pass on to regular question method
        return self.biostar_question_redirect(trans, payload)

    @web.expose
    def biostar_tool_bug_report(self, trans, hda=None, email=None, message=None):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool error.
        """
        try:
            error_reporter = biostar.BiostarErrorReporter(hda, trans.app)
            payload = error_reporter.send_report(trans.user, email=email, message=message)
        except Exception as e:
            return error(str(e))
        return self.biostar_redirect(trans, payload=payload, biostar_action='new_post')

    @web.expose
    def biostar_logout(self, trans):
        """
        Log out of biostar
        """
        try:
            url = biostar.biostar_log_out(trans)
        except Exception as e:
            return error(str(e))
        if url:
            return trans.response.send_redirect(url)
        return error("Could not determine Biostar logout URL.")
