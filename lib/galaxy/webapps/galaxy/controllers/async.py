"""
Upload class
"""

import logging
import urllib

from galaxy import jobs, web
from galaxy.util import Params
from galaxy.util.hash_util import hmac_new
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger( __name__ )


class ASync( BaseUIController ):

    @web.expose
    def default(self, trans, tool_id=None, data_id=None, data_secret=None, **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index( trans, tool_id=tool_id, data_id=data_id, data_secret=data_secret, **kwd)

    @web.expose
    def index(self, trans, tool_id=None, data_secret=None, **kwd):
        """Manages ascynchronous connections"""

        if tool_id is None:
            return "tool_id argument is required"
        tool_id = str(tool_id)

        # redirect to main when getting no parameters
        if not kwd:
            return trans.response.send_redirect( "/index" )

        params = Params(kwd, sanitize=False)
        STATUS = params.STATUS
        URL = params.URL
        data_id = params.data_id

        log.debug('async dataid -> %s' % data_id)
        trans.log_event( 'Async dataid -> %s' % str(data_id) )

        # initialize the tool
        toolbox = self.get_toolbox()
        tool = toolbox.get_tool( tool_id )
        if not tool:
            return "Tool with id %s not found" % tool_id

        #
        # we have an incoming data_id
        #
        if data_id:
            if not URL:
                return "No URL parameter was submitted for data %s" % data_id
            data = trans.sa_session.query( trans.model.HistoryDatasetAssociation ).get( data_id )

            if not data:
                return "Data %s does not exist or has already been deleted" % data_id

            if STATUS == 'OK':
                key = hmac_new( trans.app.config.tool_secret, "%d:%d" % ( data.id, data.history_id ) )
                if key != data_secret:
                    return "You do not have permission to alter data %s." % data_id
                # push the job into the queue
                data.state = data.blurb = data.states.RUNNING
                log.debug('executing tool %s' % tool.id)
                trans.log_event( 'Async executing tool %s' % tool.id, tool_id=tool.id )
                galaxy_url = trans.request.base + '/async/%s/%s/%s' % ( tool_id, data.id, key )
                galaxy_url = params.get("GALAXY_URL", galaxy_url)
                params = dict( URL=URL, GALAXY_URL=galaxy_url, name=data.name, info=data.info, dbkey=data.dbkey, data_type=data.ext )
                # Assume there is exactly one output file possible
                params[tool.outputs.keys()[0]] = data.id
                tool.execute( trans, incoming=params )
            else:
                log.debug('async error -> %s' % STATUS)
                trans.log_event( 'Async error -> %s' % STATUS )
                data.state = data.blurb = jobs.JOB_ERROR
                data.info = "Error -> %s" % STATUS

            trans.sa_session.flush()

            return "Data %s with status %s received. OK" % (data_id, STATUS)
        else:
            #
            # no data_id must be parameter submission
            #
            if params.data_type:
                GALAXY_TYPE = params.data_type
            elif params.galaxyFileFormat == 'wig':  # this is an undocumented legacy special case
                GALAXY_TYPE = 'wig'
            else:
                GALAXY_TYPE = params.GALAXY_TYPE or tool.outputs.values()[0].format

            GALAXY_NAME = params.name or params.GALAXY_NAME or '%s query' % tool.name
            GALAXY_INFO = params.info or params.GALAXY_INFO or params.galaxyDescription or ''
            GALAXY_BUILD = params.dbkey or params.GALAXY_BUILD or params.galaxyFreeze or '?'

            # data = datatypes.factory(ext=GALAXY_TYPE)()
            # data.ext   = GALAXY_TYPE
            # data.name  = GALAXY_NAME
            # data.info  = GALAXY_INFO
            # data.dbkey = GALAXY_BUILD
            # data.state = jobs.JOB_OK
            # history.datasets.add_dataset( data )

            data = trans.app.model.HistoryDatasetAssociation( create_dataset=True, sa_session=trans.sa_session, extension=GALAXY_TYPE )
            trans.app.security_agent.set_all_dataset_permissions( data.dataset, trans.app.security_agent.history_get_default_permissions( trans.history ) )
            data.name = GALAXY_NAME
            data.dbkey = GALAXY_BUILD
            data.info = GALAXY_INFO
            trans.sa_session.add( data )  # Need to add data to session before setting state (setting state requires that the data object is in the session, but this may change)
            data.state = data.states.NEW
            open( data.file_name, 'wb' ).close()  # create the file
            trans.history.add_dataset( data, genome_build=GALAXY_BUILD )
            trans.sa_session.add( trans.history )
            trans.sa_session.flush()
            trans.log_event( "Added dataset %d to history %d" % (data.id, trans.history.id ), tool_id=tool_id )

            try:
                key = hmac_new( trans.app.config.tool_secret, "%d:%d" % ( data.id, data.history_id ) )
                galaxy_url = trans.request.base + '/async/%s/%s/%s' % ( tool_id, data.id, key )
                params.update( { 'GALAXY_URL': galaxy_url } )
                params.update( { 'data_id': data.id } )
                # Use provided URL or fallback to tool action
                url = URL or tool.action
                # Does url already have query params?
                if '?' in url:
                    url_join_char = '&'
                else:
                    url_join_char = '?'
                url = "%s%s%s" % ( url, url_join_char, urllib.urlencode( params.flatten() ) )
                log.debug("connecting to -> %s" % url)
                trans.log_event( "Async connecting to -> %s" % url )
                text = urllib.urlopen(url).read(-1)
                text = text.strip()
                if not text.endswith('OK'):
                    raise Exception( text )
                data.state = data.blurb = data.states.RUNNING
            except Exception as e:
                data.info = str(e)
                data.state = data.blurb = data.states.ERROR

            trans.sa_session.flush()

        return trans.fill_template( 'root/tool_runner.mako', out_data={}, num_jobs=1, job_errors=[] )
