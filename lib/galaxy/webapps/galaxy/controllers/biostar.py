"""
Support for integration with the Biostar Q&A application
"""

from galaxy.web.base.controller import BaseUIController, url_for, error, web

import base64
import json
import hmac

# Biostar requires all keys to be present, so we start with a template
DEFAULT_PAYLOAD = {
    'email': "", 
    'title': "Question about Galaxy", 
    'tags': 'galaxy',
    'tool_name': '', 
    'tool_version': '', 
    'tool_id': ''
}

def encode_data( key, data ):
    """
    Encode data to send a question to Biostar
    """
    text = json.dumps(data)
    text = base64.urlsafe_b64encode(text)
    digest = hmac.new(key, text).hexdigest()
    return text, digest


class BiostarController( BaseUIController ):
    """
    Provides integration with Biostar through external authentication, see: http://liondb.com/help/x/
    """

    @web.expose
    def biostar_redirect( self, trans, payload={}, biostar_action=None ):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool.
        """
        # Ensure biostar integration is enabled
        if not trans.app.config.biostar_url:
            return error( "Biostar integration is not enabled" )
        # Start building up the payload
        payload = dict( DEFAULT_PAYLOAD, **payload )
        # Do the best we can of providing user information for the payload
        if trans.user:
            payload['email'] = trans.user.email
            if trans.user.username:
                payload['username'] = trans.user.username
                payload['display_name'] = trans.user.username
            else:
                payload['display_name'] = "Galaxy User"
        else:
            payload['username'] = payload['display_name'] = "Anonymous Galaxy User %d" % trans.galaxy_session.id
        data, digest = encode_data( trans.app.config.biostar_key, payload )
        return trans.response.send_redirect( url_for( trans.app.config.biostar_url, data=data, digest=digest, name=trans.app.config.biostar_key_name, action=biostar_action ) )

    @web.expose
    def biostar_question_redirect( self, trans, payload={} ):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool.
        """
        return self.biostar_redirect( trans, payload=payload, biostar_action='new' )

    @web.expose
    def biostar_tool_question_redirect( self, trans, tool_id=None ):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool.
        """
        # tool_id is required
        if tool_id is None:
            return error( "No tool_id provided" )
        # Load the tool
        tool_version_select_field, tools, tool = \
            self.app.toolbox.get_tool_components( tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=True )
        # No matching tool, unlikely
        if not tool:
            return error( "No tool found matching '%s'" % tool_id )
        # Tool specific information for payload
        payload = { 'title': "Question about Galaxy tool '%s'" % tool.name, 'tool_name': tool.name, 'tool_version': tool.version, 'tool_id': tool.id }
        # Pass on to regular question method
        return self.biostar_question_redirect( trans, payload )