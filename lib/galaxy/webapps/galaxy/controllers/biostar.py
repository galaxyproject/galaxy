"""
Support for integration with the Biostar Q&A application
"""

from galaxy.web.base.controller import BaseUIController, url_for, error, web

import base64
from galaxy.util import json
import hmac
import urlparse

# Slugifying from Armin Ronacher (http://flask.pocoo.org/snippets/5/)

import re
from unicodedata import normalize

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

BIOSTAR_ACTIONS = {
    None: '',
    'new': 'p/new/post/',
    'show_tag_galaxy': 't/galaxy/'
}


def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


# Biostar requires all keys to be present, so we start with a template
DEFAULT_PAYLOAD = {
    'title': '',
    'tag_val': 'galaxy',
    'content': '',
}


def encode_data( key, data ):
    """
    Encode data to send a question to Biostar
    """
    text = json.to_json_string(data)
    text = base64.urlsafe_b64encode(text)
    digest = hmac.new(key, text).hexdigest()
    return text, digest


def tag_for_tool( tool ):
    """
    Generate a reasonable biostar tag for a tool.
    """
    return slugify( unicode( tool.name ) )

def determine_cookie_domain( galaxy_hostname, biostar_hostname ):
    if galaxy_hostname == biostar_hostname:
        return galaxy_hostname
    
    sub_biostar_hostname = biostar_hostname.split( '.', 1 )[-1]
    if sub_biostar_hostname == galaxy_hostname:
        return galaxy_hostname
    
    sub_galaxy_hostname = galaxy_hostname.split( '.', 1 )[-1]
    if sub_biostar_hostname == sub_galaxy_hostname:
        return sub_galaxy_hostname
    
    return galaxy_hostname

def create_cookie( trans, key_name, key, email ):
    digest = hmac.new( key, email ).hexdigest()
    value = "%s:%s" % (email, digest)
    trans.set_cookie( value, name=key_name, path='/', age=90, version='1' )
    #We need to explicitly set the domain here, in order to allow for biostar in a subdomain to work
    galaxy_hostname = urlparse.urlsplit( url_for( '/', qualified=True ) ).hostname
    biostar_hostname = urlparse.urlsplit( trans.app.config.biostar_url ).hostname
    trans.response.cookies[ key_name ][ 'domain' ] = determine_cookie_domain( galaxy_hostname, biostar_hostname )

class BiostarController( BaseUIController ):
    """
    Provides integration with Biostar through external authentication, see: http://liondb.com/help/x/
    """

    @web.expose
    def biostar_redirect( self, trans, payload=None, biostar_action=None ):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool.
        """
        # Ensure biostar integration is enabled
        if not trans.app.config.biostar_url:
            return error( "Biostar integration is not enabled" )
        if biostar_action not in BIOSTAR_ACTIONS:
            return error( "Invalid action specified (%s)." % ( biostar_action ) )
        
        # Start building up the payload
        payload = payload or {}
        payload = dict( DEFAULT_PAYLOAD, **payload )
        # Do the best we can of providing user information for the payload
        if trans.user:
            email = trans.user.email
        else:
            email = "anon-%s" % ( trans.security.encode_id( trans.galaxy_session.id ) )
        create_cookie( trans, trans.app.config.biostar_key_name, trans.app.config.biostar_key, email )
        return trans.response.send_redirect( url_for( urlparse.urljoin( trans.app.config.biostar_url, BIOSTAR_ACTIONS[ biostar_action ] ), **payload ) )

    @web.expose
    def biostar_question_redirect( self, trans, payload=None ):
        """
        Generate a redirect to a Biostar site using external authentication to
        pass Galaxy user information and information about a specific tool.
        """
        payload = payload or {}
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
        payload = { 'title':'Need help with "%s" tool' % ( tool.name ),
                    'content': '<br /><hr /><p>Tool name: %s</br>Tool version: %s</br>Tool ID: %s</p>' % ( tool.name, tool.version, tool.id ),
                    'tag_val': 'galaxy ' + tag_for_tool( tool ) }
        # Pass on to regular question method
        return self.biostar_question_redirect( trans, payload )
