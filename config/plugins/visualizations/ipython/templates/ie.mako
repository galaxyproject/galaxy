<%!
import ConfigParser
import os
import shlex
import subprocess
import random

viz_id = None
%>

<%def name="set_id(name)"%>
<%
    viz_id = name
%>
</%def>

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

<%def name="proxy_request_port()">
<%
    """
        Refactor of our port getting...eventually this will be replaced with an API call instead.
    """
    # Find all ports that are already occupied
    cmd_netstat = shlex.split("netstat -tuln")
    p1 = subprocess.Popen(cmd_netstat, stdout=subprocess.PIPE)

    occupied_ports = set()
    for line in p1.stdout.read().split('\n'):
        if line.startswith('tcp') or line.startswith('tcp6'):
            col = line.split()
            local_address = col[3]
            local_port = local_address.split(':')[-1]
            occupied_ports.add( int(local_port) )

    # Generate random free port number for our docker container
    while True:
        port = random.randrange(10000,15000)
        if port not in occupied_ports:
            break
    return port
%>
</%def>

<%def name="generate_password(length)">
<%
    return ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(length))
%>
</%def>

<%def name="javascript_boolean(length)">
<%
    """
        Convenience function to convert boolean for use in JS
    """
    if boolean:
        return "true";
    else:
        return "false"
%>
</%def>


<%def name="docker_cmd(ipy_viz_config, PORT, temp_dir)">
<%
    return '%s run -d --sig-proxy=true -p %s:6789 -v "%s:/import/" %s' % \
        (ipy_viz_config.get("docker", "command"), PORT, temp_dir, ipy_viz_config.get("docker",
                                                                                     "image"))
%>
</%def>
