"""
Galaxy web application framework
"""

from galaxy import eggs
eggs.require( "pexpect" )
eggs.require( "amqp" )

import base
url_for = base.routes.url_for
