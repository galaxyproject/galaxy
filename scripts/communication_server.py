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
    <title>Chat</title>
</head>
<body overflow="hidden"> 
    <div id="all_messages" class="messages" style="overflow: auto; height: 300px;"></div>

    <div class="send_message" style="margin-top:15px;">
    <form id="broadcast" method="POST" action='#'>
        <textarea rows="4" cols="100" name="broadcast_data" id="broadcast_data" placeholder="type your message..."></textarea>
        <input type="submit" value="Send Message">
        <input type="button" value="Disconnect" id="disconnect">
    </form>
    </div>

    <script type="text/javascript" src="https://code.jquery.com/jquery-1.10.2.js"></script>
    <script type="text/javascript" src="//cdnjs.cloudflare.com/ajax/libs/socket.io/1.3.5/socket.io.min.js"></script>
    <script type="text/javascript" charset="utf-8">
        $(document).ready(function(){
            // the namespace events connect to 
            namespace = '/chat'; 

            // connect io socket to the current server
            var socket = io.connect( window.location.protocol + '//' + document.domain + ':' + location.port + namespace );
            
            // fill the messages if user is already connected 
            // and comes back to the chat window
            fill_messages();

            // event handler for server sent data
            // append all the messages broadcasted
            socket.on('event response', function( msg ) {
                var orig_message = msg.data.split(':'),
                    from_uid = orig_message[1].split('-')[1],
                    message = unescape(orig_message[1].split('-')[0]) + ": " + unescape(orig_message[0]),
                    uid = get_userid(),
                    $all_messages = $('#all_messages');
                // append only for non empty messages
                if( orig_message[0].length > 0 ) {
                        $( '#all_messages' ).append( $('<div' + '/' + '>' ).text( message ).html() );
                        $( '#all_messages' ).append('<br><br>');
		}
                // updates the user session storage with all the messages
                sessionStorage[uid]  = $all_messages.html();
                // show the last item by scrolling to the end
                scroll_to_last($all_messages);                
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
                send_data.data = escape( $( '#broadcast_data' ).val() ) + ':' + get_userdata();
                socket.emit( 'event broadcast', send_data );
                $( '#broadcast_data' ).val('');
                return false;
            });

            // disconnet the user from the chat server
            $('#disconnect').click(function(event){
                var send_data = { }
                    uid = get_userid();
                send_data.data = "disconnected" + ":" + get_username();
		socket.emit( 'event disconnect', send_data );
                sessionStorage.removeItem(uid);
                return false
	    });
        });

        // get the current username of logged in user
        // from the querystring of the URL
        function get_userdata() {
                var user_data = $('.modal-body').context.URL.split('?')[1],
                    data = user_data.split('&'),
                    userid_data = data[1],
                    username_data = data[0];
                if(data) {
			return unescape( username_data.split('=')[1] + "-" + userid_data.split('=')[1] );
		}
		else {
			return "";	
		}
	}

	// fill in all messages
        function fill_messages() {
                var uid = get_userid(),
                    message_html = $.parseHTML( sessionStorage[uid] ),
		    $all_messages = $('#all_messages');
		if(sessionStorage[uid]) {
			$all_messages.append( $( '<div' + '/' + '>' ).html( message_html ) );
		}
                // show the last item by scrolling to the end
                scroll_to_last($all_messages);
	}

	// gets the user id
        function get_userid() {
		return get_userdata().split('-')[1];
	}

        // gets the user name
        function get_username() {
		return get_userdata().split('-')[0];
	}

	// scrolls to the last of element
        function scroll_to_last($el) {
		$el.scrollTop( $el[0].scrollHeight );
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
    print("connected")
    

@socketio.on('event broadcast', namespace='/chat')
def event_broadcast(message):
    emit( 'event response',
         { 'data': message['data']}, broadcast=True )


@socketio.on('event disconnect', namespace='/chat')
def event_disconnect(message):
    print("disconnected")
    disconnect()


@socketio.on('disconnect', namespace='/chat')
def event_disconnect():
    print("disconnected")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Real-time communication server for Galaxy.')
    parser.add_argument('--port', type=int, default="7070", help='Port number on which the server should run.')
    parser.add_argument('--host', default='localhost', help='Hostname of the communication server.')

    args = parser.parse_args()
    socketio.run(app, host=args.host, port=args.port)

