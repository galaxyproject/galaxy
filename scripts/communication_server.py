#!/usr/bin/env python

"""
Server for realtime Galaxy communication.


At first you need to install a few requirements.

. GALAXY_ROOT/.venv/bin/activate    # activate Galaxy's virtualenv
pip install flask flask-socketio eventlet   # install the requirements



As a next step start the communication server with something like this:

./scripts/communication_server.py --port 7070 --host localhost

Please make sure the host and the port matches the ones on config/galaxy.ini

The communication server feature of Galaxy can be controlled on three different levels:
  1. Admin can activate/deactivate communication (config/galaxy.ini)
  2. User can actrivate/deactivate for one session (in the communication window)
  3. User can actrivate/deactivate as personal-setting for ever (Galaxy user preferences)


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
   <script src="https://use.fontawesome.com/89a733ecb7.js"></script>
    <style>
    html, body {
        height: 100%;
    }
    /* Styles for message text box */
    .clearable{
      background: #fff url(http://i.stack.imgur.com/mJotv.gif) no-repeat right -10px center;
      border: 1px solid #999;
      padding: 3px 18px 3px 4px;
      border-radius: 3px;
      transition: background 0.4s;
    }
    .clearable.x  { background-position: right 5px center; }
    .clearable.onX{ cursor: pointer; }
    .clearable::-ms-clear {display: none; width:0; height:0;}
    .size {
        height: 40px;
        width: 96%;
        margin-bottom:5px;
    }

    /* Styles for top right icons */
    .right_icons {
        margin-left: 83.5%;
    }
    .user,
    .anchor {
        cursor: pointer;
        color: black;
    }
    .messages {
        overflow-y: auto;
        height: 72%;
    }
    .send_message {
        margin-top: 5px;
   }
    .conn_msg {
        color: #00FF00;
        font-style: italic;
        font-size: 14px;
    }
    .disconn_msg {
        color: #FF0000;
        font-style: italic;
        font-size: 14px;
    }
    .user_name {
        font-style: italic;
        font-size: 13px;
    }
    .user_message {
        font-size: 14px;
        background-color: #DFE5F9;
        width: 99%;
    }
    .date_time {
        font-style: italic;
        font-size: 13px;
    }
    .date_time span {
        float: right;
    }
    </style>
</head>
<body style="overflow: hidden; height: 100%";>
    <div style="float: left"></div>
    <div class="right_icons">
        <i id="online_status" class="anchor fa fa-comments" aria-hidden="true" title=""></i>
        <i class="user fa fa-user" aria-hidden="true" title=""></i>
        <i id="chat_history" class="anchor fa fa-history" aria-hidden="true" title="Show chat history"></i>
        <i id="delete_history" class="anchor fa fa-chain-broken" aria-hidden="true" title="Delete full history"></i>
        <i id="clear_messages" class="anchor fa fa-trash-o" aria-hidden="true" title="Clear all messages"></i>
    </div>
    <div id="all_messages" class="messages"></div>
    <div class="send_message">
        <input id="send_data" class="size clearable" type="text" placeholder="Type your message..." autocomplete="off" />
    </div>

    <script type="text/javascript" src="https://code.jquery.com/jquery-1.10.2.js"></script>
    <script type="text/javascript" src="//cdnjs.cloudflare.com/ajax/libs/socket.io/1.3.5/socket.io.min.js"></script>
    <script type="text/javascript" charset="utf-8">
    // the namespace events connect to
    var namespace = '/chat',
    socket = io.connect( window.location.protocol + '//' + document.domain + ':' + location.port + namespace);
    // socketio events
    var events_module = {
        // event handler for sent data from server
        event_response: function( socket ) {
            socket.on('event response', function( msg ) {
                var orig_message = msg.data.split(':'),
                    message = "",
                    uid = utils.get_userid(),
                    $el_all_messages = $('#all_messages');
                // builds the message to be displayed
                message = utils.build_message( orig_message, uid );
                // append only for non empty messages
                if( orig_message[0].length > 0 ) {
                    utils.append_message( $el_all_messages, message );
                    // adding message to build full chat history
                    if( !localStorage[uid] ) {
                        localStorage[uid] = message + '<br>';
                    }
                    else {
                        localStorage[uid] = localStorage[uid] + message + '<br>';
                    }
                }
                // updates the user session storage with all the messages
                sessionStorage[uid] = $el_all_messages.html();
                // show the last item by scrolling to the end
                utils.scroll_to_last( $el_all_messages );
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
            $('#send_data').keydown(function( event ) {
                if( event.keyCode == 13 || event.which == 13 ) {
                    if( click_events.is_connected ) {
                        var send_data = { };
                        send_data.data = escape( $( '#send_data' ).val() ) + ':' + utils.get_userdata();
                        socket.emit( 'event broadcast', send_data );
                        $( '#send_data' ).val( '' );
                    }
                    return false;
                }
            });
        },
        // event for connected and disconneted states
        connect_disconnect: function( socket ) {
            $( '#online_status' ).click(function() {
                var $el_online_status = $( '#online_status' ),
                    $el_input_text = $( '#send_data' ),
                    send_data = { }
                    connected_message = 'Type your message...',
                    uid = utils.get_userid();
                if( click_events.is_connected ) {
                    click_events.make_disconnect( uid, $el_input_text, $el_online_status );
                }
                else {
                    socket.connect();
                    click_events.is_connected = true;
                    sessionStorage['connected'] = true;
                    utils.update_online_status( $el_online_status, click_events.is_connected );
                    $el_input_text.prop( 'disabled', false );
                    $el_input_text.val( '' );
                    $el_input_text.prop( 'placeholder', connected_message );
                }
            });
        },
        // clear all the messages
        clear_messages: function() {
        $( '#clear_messages' ).click(function( event ) {
                // clears all the messages
                utils.clear_message_area();
                return false;
            });
        },
        // shows full chat history
        show_chat_history: function() {
            $( '#chat_history' ).click( function( events ) {
                utils.fill_messages( localStorage[utils.get_userid()] );
            });
        },
        // delete full history
        delete_history: function() {
            $( '#delete_history' ).click( function() {
                var uid = utils.get_userid();
                localStorage.removeItem(uid);
                sessionStorage.removeItem( uid );
                utils.clear_message_area();
            });
        },
        // makes disconnect
        make_disconnect: function(uid, $el_input_text, $el_online_status) {
            var send_data = {}
                disconnected_message = 'You are now disconnected. To send/receive messages, please connect';
            click_events.is_connected = false;
            send_data.data = "disconnected" + ":" + utils.get_username();
            socket.emit( 'event disconnect', send_data );
            sessionStorage.removeItem( uid );
            sessionStorage['connected'] = false;
            utils.update_online_status( $el_online_status, click_events.is_connected );
            $el_input_text.val( '' );
            $el_input_text.prop( 'placeholder', disconnected_message );
            $el_input_text.prop( 'disabled', true );
        }
    }
    // utility methods
    var utils = {
        // get the current username of logged in user
        // from the querystring of the URL
        get_userdata: function() {
            var $el_modal_body = $('.modal-body'),
                user_data = $el_modal_body.context.URL.split('?')[1],
                data = user_data.split('&'),
                userid_data = data[1],
                username_data = data[0];
                if( data ) {
                    return unescape( username_data.split('=')[1] + "-" + userid_data.split('=')[1] );
                }
                else {
                   return "";
               }
        },
        // fill in all messages
        fill_messages: function ( collection ) {
            var uid = utils.get_userid(),
            message_html = $.parseHTML( collection ),
            $el_all_messages = $('#all_messages');
            // clears the previous items
            this.clear_message_area();
            if(collection) {
                $el_all_messages.append( $( '<div' + '/' + '>' ).html( message_html ) );
            }
            // show the last item by scrolling to the end
            utils.scroll_to_last($el_all_messages);
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
        append_message: function( $el, message ) {
            $el.append( message );
            $el.append( '<br>' );
        },
        // builds message
        build_message: function(original_message, uid) {
            var from_uid = original_message[1].split('-')[1],
                message_user = "",
                message_text = "";
            // for user's own messages
            if ( from_uid === uid ) {
                message_user = this.build_message_username_template( 'me' );
            }
            // for other user's messages
            else {
                message_user = this.build_message_username_template( unescape( original_message[1].split('-')[0] ) );
            }
            message_text = this.build_message_template( original_message );
            return message_user + message_text;
        },
        // builds message template
        build_message_template: function( original_message ) {
            return "<div class='user_message'>" +
                       "<i class='fa fa-quote-left' aria-hidden='true'></i> " + unescape( original_message[0] ) +
                       "<i class='fa fa-quote-right' aria-hidden='true'></i>" +
                       "<div class='date_time'><span title=" + this.get_date() + ">" +
                       "<i class='fa fa-clock-o' aria-hidden='true'></i> " + this.get_time() + "</span>" +
                   "</div></div>";
        },
        // builds template for username for message display
        build_message_username_template: function(username) {
            return "<span class='user_name'>" + username + "<br></span>";
        },
        // adds an information about the online status
        update_online_status: function( $el, connected ) {
            if( connected ) {
                $el.prop( "title", "You are online!" ).css( "color", "#00FF00" );
            }
            else {
                $el.prop( "title", "You are offline!" ).css( "color", "#FF0000");
            }
        },
        // gets the current date and time
        get_time: function() {
            var currentdate = new Date(),
                datetime = "",
                hours = 0,
                minutes = 0;
                hours = ( currentdate.getHours() < 10 ) ? ( "0" + currentdate.getHours() ) : currentdate.getHours();
                minutes = ( currentdate.getMinutes() < 10 ) ? ( "0" + currentdate.getMinutes() ) : currentdate.getMinutes();
                datetime = hours + ":" + minutes;
                return datetime;
        },
        get_date: function() {
            var currentdate = new Date(),
                day,
                month;
            month = ( (currentdate.getMonth()+1 ) < 10) ? ( "0" + (currentdate.getMonth()+1) ) : ( currentdate.getMonth()+1 );
            day = ( currentdate.getDate() < 10 ) ? ( "0" + currentdate.getDate() ) : currentdate.getDate();
            return month + "/" + day + "/" + currentdate.getFullYear();
        },
        set_user_info: function() {
            $( '.user' ).prop( 'title', this.get_username() );
        },
        clear_message_area: function() {
            $('#all_messages').html("");
        },
    }
    // this snippet is for adding a clear icon in the message textbox
    function tog(v){return v?'addClass':'removeClass';}
    $(document).on('input', '.clearable', function(){
        $(this)[tog(this.value)]('x');
    }).on('mousemove', '.x', function( e ){
        $(this)[tog(this.offsetWidth-18 < e.clientX-this.getBoundingClientRect().left)]('onX');
    }).on('touchstart click', '.onX', function( ev ){
        ev.preventDefault();
        $(this).removeClass('x onX').val('').change();
    });
    // registers the events when this document is ready
        $(document).ready(function(){
            // fill the messages if user is already connected
            // and comes back to the chat window
            var uid = utils.get_userid();
            utils.fill_messages(sessionStorage[uid]);
            // updates online status text
            // by checking if user was connected or not
            if(sessionStorage['connected']) {
                if(sessionStorage['connected'] === 'true' || sessionStorage['connected'] === true) {
                    utils.update_online_status( $('#online_status'), true );
                    click_events.is_connected = true;
                }
                else {
                    click_events.make_disconnect( uid, $('#send_data'), $('#online_status') );
                    utils.clear_message_area();
                }
            }
            else {
                utils.update_online_status( $('#online_status'), true );
                click_events.is_connected = true;
            }
            // set user info to the user icon
            utils.set_user_info();
            // registers response event
            events_module.event_response(socket);
            // registers connect event
            events_module.event_connect(socket);
            // broadcast the data
            click_events.broadcast_data(socket);
            // disconnet the user from the chat server
            click_events.connect_disconnect(socket);
            // show chat history
            click_events.show_chat_history();
            // clears all the messages
            click_events.clear_messages();
            // deletes full chat history
            click_events.delete_history();
            //utils.get_time();
            utils.scroll_to_last( $('#all_messages') );
       });
    </script>
</body>
</html>"""


@app.route('/')
@crossdomain(origin='*')
def index():
    return template


@socketio.on('event connect', namespace='/chat')
def event_connect(message):
    print("connected")


@socketio.on('event broadcast', namespace='/chat')
def event_broadcast(message):
    emit('event response',
         {'data': message['data']}, broadcast=True)


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

