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
    <div id="all_messages" class="messages" style="overflow: auto; height: 295px;"></div>

    <div class="send_message" style="margin-top:15px;">
    <form id="broadcast" method="POST" action='#'>
        <textarea rows="4" cols="100" name="broadcast_data" id="broadcast_data" placeholder="type your message..."></textarea>
        <input type="submit" value="Send Message">
        <input type="button" value="Clear" id="clear">
        <input type="button" value="Clear All Messages" id="clear_messages">
        <input type="button" value="Disconnect" id="disconnect">
        <label id="online_status" style="margin-left:5px;"><label>
    </form>
    
    </div>

    <script type="text/javascript" src="https://code.jquery.com/jquery-1.10.2.js"></script>
    <script type="text/javascript" src="//cdnjs.cloudflare.com/ajax/libs/socket.io/1.3.5/socket.io.min.js"></script>
    <script type="text/javascript" charset="utf-8">
        
        // the namespace events connect to 
        var namespace = '/chat';
      
        // socketio events
        var events_module = {
                // makes socket connection 
        connect_socket: function( namespace ) {
            var socket = io.connect( window.location.protocol + '//' + document.domain + ':' + location.port + namespace );
                return socket;
        },
        // event handler for sent data from server
        event_response: function( socket ) {
            socket.on('event response', function( msg ) {
                var orig_message = msg.data.split(':'),
                    message = "",
                    uid = utils.get_userid(),
                    $all_messages = $('#all_messages');
                            // builds the message to be displayed
                            message = utils.build_message( orig_message, uid );
                // append only for non empty messages
                if( orig_message[0].length > 0 ) {
                        utils.append_message($all_messages, message);
            }
                // updates the user session storage with all the messages
                sessionStorage[uid]  = $all_messages.html();
                // show the last item by scrolling to the end
                utils.scroll_to_last($all_messages);
            });
        },
        // event handler for new connections
                event_connect: function( socket ) {
            socket.on( 'connect', function() {
                var send_data = { };
                send_data.data = 'connected' + ':' + utils.get_username();
                socket.emit( 'event connect', send_data );
            });
        }
    }

        // all the click events of buttons
        var click_events = {
                // on form load, user is connected, so the value is true
                is_connected: true,

        broadcast_data: function(socket) {
            $( 'form#broadcast' ).submit( function( event ) {
                                // send data only when connected
                                if( click_events.is_connected ) {
                    var send_data = { };
                    send_data.data = escape( $( '#broadcast_data' ).val() ) + ':' + utils.get_userdata();
                    socket.emit( 'event broadcast', send_data );
                    $( '#broadcast_data' ).val('');
                }
                return false;
                    });
        },
        
                disconnect: function(socket) {
            $( '#disconnect' ).click(function( event ){
                                // disconnect only if connected
                if (click_events.is_connected) {
                    var send_data = { }
                        uid = utils.get_userid(),
                        $all_messages = $( '#all_messages' );
                    send_data.data = "disconnected" + ":" + utils.get_username();
                    socket.emit( 'event disconnect', send_data );
                    sessionStorage.removeItem(uid);
                    utils.append_message( $all_messages, "You are disconnected and can't send/receive messages..." );
                    utils.scroll_to_last( $all_messages );
                                click_events.is_connected = false;
                    utils.update_online_status( $('#online_status'), click_events.is_connected );
                }
                return false;
                });
        },

        clear: function() {
            $( '#clear' ).click(function( event ){
                                // clears the textarea
                        $("#broadcast_data").val("");
                        return false;
                });
        },

        clear_messages: function() {
            $( '#clear_messages' ).click(function( event ){
                                // clears all the messages
                        $("#all_messages").html("");
                        return false;
                });
        },
    
    }

        // utility methods
        var utils = {
                // get the current username of logged in user
            // from the querystring of the URL
        get_userdata: function() {
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
        },

                // fill in all messages
        fill_messages: function () {
            var uid = utils.get_userid(),
                message_html = $.parseHTML( sessionStorage[uid] ),
                $all_messages = $('#all_messages');
            if(sessionStorage[uid]) {
                $all_messages.append( $( '<div/>' ).html( message_html ) );
            }
            // show the last item by scrolling to the end
            utils.scroll_to_last($all_messages);
        },

        // gets the user id
        get_userid: function() {
            return utils.get_userdata().split('-')[1];
        },

        // gets the user name
        get_username: function() {
            return utils.get_userdata().split('-')[0];
        },

        // scrolls to the last of element
        scroll_to_last: function($el) {
            $el.scrollTop( $el[0].scrollHeight );
        },

        // append message 
        append_message: function($el, message) {
            $el.append( $('<div' + '/' + '>' ).text( message ).html() );
                $el.append('<br><br>');
        },
                // builds message 
                build_message: function(original_message, uid) {
                    var from_uid = original_message[1].split('-')[1];
                        if ( from_uid === uid ) {
                return "Me: " + unescape(original_message[0]);
            }
            else {
                return unescape(original_message[1].split('-')[0]) + ": " + unescape(original_message[0]);
            }
        },
                // adds an information about the online status
                update_online_status: function( $el, connected ) {
            if( connected ) {
                $el.text( "You are online!" );
                $el.css( "color", "#006400" );
            }
            else {
                $el.text("You are offline!");
                    $el.css( "color", "#B22222 ");
            }
        }
    }

        // registers the events when this document is ready
        $(document).ready(function(){
        // connect io socket to the current server
        var socket =  events_module.connect_socket( namespace );

        // fill the messages if user is already connected 
        // and comes back to the chat window
        utils.fill_messages();
        // updates online status text
        utils.update_online_status( $('#online_status'), true );
        // registers response event
        events_module.event_response(socket);
        // registers connect event
        events_module.event_connect(socket);

        // broadcast the data
        click_events.broadcast_data(socket);
        // disconnet the user from the chat server
        click_events.disconnect(socket);
        // clears the textarea
        click_events.clear();
        // clears all the messages
        click_events.clear_messages();
        });

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

