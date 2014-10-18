<%!
import ConfigParser
import os
somevar = ["one", "two", "three"]
%>

<%def name="get_galaxy_paster_port(galaxy_root_dir, galaxy_config)">
  <%
    config = ConfigParser.SafeConfigParser({'port': '8080'})
    config.read( os.path.join( galaxy_root_dir, 'universe_wsgi.ini' ) )

    # uWSGI galaxy installations don't use paster and only speak uWSGI not http
    try:
        port = config.getint('server:%s' % galaxy_config.server_name, 'port')
    except:
        port = None
    return port
  %>
</%def>

