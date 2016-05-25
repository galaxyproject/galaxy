#!/usr/bin/env python

"""
Server for realtime Galaxy communication.


At first you need to install a few requirements.

. GALAXY_ROOT/.venv/bin/activate    # activate Galaxy's virtualenv
pip install flask flask-socketio eventlet   # install the requirements



As a next step start the communication server with something like this:

./scripts/communication_server.py --port 7070 --host localhost

Please make sure the host and the port matches the ones on config/galaxy.ini

"""


import sys
import argparse
from flask import Flask, request, make_response, current_app
from flask_socketio import SocketIO, emit, disconnect
from datetime import timedelta
from functools import update_wrapper

app = Flask(__name__)
app.config['SECRET_KEY'] = 'notscret'
socketio = SocketIO(app)


# Taken from flask.pocoo.org/snippets/56/

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


template = """<!DOCTYPE HTML>
<html>
<head>
    <title>Real-time communication for Galaxy</title>
</head>
<body> 

    <form id="broadcast" method="POST" action='#'>
        <input type="text" name="broadcast_data" id="broadcast_data" placeholder="type your message...">
        <input type="submit" value="Send">
    </form>
    <h3>All messages</h3>
    <div id="log"></div>

    <script type="text/javascript" src="//code.jquery.com/jquery-1.4.2.min.js"></script>
    <script type="text/javascript" src="//cdnjs.cloudflare.com/ajax/libs/socket.io/1.3.5/socket.io.min.js"></script>
    <script type="text/javascript" charset="utf-8">
        $(document).ready(function(){
            // the namespace events connect to 
            namespace = '/chat'; 

            // connect io socket to the current server
            var socket = io.connect( window.location.protocol + '//' + document.domain + ':' + location.port + namespace );
              
            // event handler for server sent data
            // append all the messages broadcasted
            socket.on('event response', function( msg ) {
                var orig_message = msg.data.split(':'),
                    message = unescape(orig_message[1]) + ": " + unescape(orig_message[0]);
                $('#log').append('<br>' + $('<div' + '/' + '>').text( message ).html());
            });

            // event handler for new connections
            socket.on('connect', function() {
                var send_data = { };
                send_data.data = 'connected' + ':' + get_username();
                socket.emit( 'event connect', send_data );
            });

            // broadcast the data
            $('form#broadcast').submit( function( event ) {
                var send_data = { };
                send_data.data = escape( $( '#broadcast_data' ).val() ) + ':' + get_username();
                socket.emit( 'event broadcast', send_data );
                $( '#broadcast_data' ).val('');
                return false;
            });
            
        });
        // get the current username of logged in user
        // from the querystring of the URL
        function get_username() {
                var username_keyvalue = $('.modal-body').context.URL.split('?')[1];
                if(username_keyvalue) {
                    return unescape(username_keyvalue.split('=')[1]);
        }
        else {
            return "";
        }

}

    </script>
</body>
</html>
"""

@app.route('/')
@crossdomain(origin='*')
def index():
    return template


@socketio.on('event connect', namespace='/chat')
def event_connect(message):
    emit( 'event response',
         { 'data': message['data'] },  broadcast=True )


@socketio.on('event broadcast', namespace='/chat')
def event_broadcast(message):
    print(message)
    emit( 'event response',
         { 'data': message['data']}, broadcast=True )


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Real-time communication server for Galaxy.')
    parser.add_argument('--port', type=int, default="7070", help='Port number on which the server should run.')
    parser.add_argument('--host', default='localhost', help='Hostname of the communication server.')

    args = parser.parse_args()
    socketio.run(app, host=args.host, port=args.port)

