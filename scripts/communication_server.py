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
   <link href="../static/style/base.css" media="screen" rel="stylesheet" type="text/css">
    <style>
        /* Styles for message text box */
        .clearable{
      background: #fff url(/static/images/delete_tag_icon_gray.png) no-repeat right -10px center;
      border: 1px solid #999;
      padding: 3px 18px 3px 4px;
      border-radius: 3px;
      transition: background 0.4s;
    }
    .clearable.x  { background-position: right 5px center; }
    .clearable.onX{ cursor: pointer; }
    .clearable::-ms-clear {display: none; width:0; height:0;}
    .size {
        height: 30px;
        width: 795px;
        margin-bottom:5px;
    }

    /* Styles for top right icons */
    .right_icons {
        margin: 0px 0px 10px 705px;
    }
    .user,
    .connect_disconnect,
    anchor {
        cursor: pointer;
        color: black;
    }
    .messages {
        overflow: auto;
        height: 365px;
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
        width: 790px;
    }
    .date_time {
        font-style: italic;
        font-size: 13px;
    }
    .date_time span {
        float:right;
    }
    .btn-send {
        visibility: hidden;
    }
    </style>
</head>
<body style="overflow: hidden";>
    <div class="right_icons">
        <i id="online_status" class="fa fa-comments" aria-hidden="true"title=""></i>
        <i class="user fa fa-user" aria-hidden="true" title=""></i>
        <i id="chat_history" class="anchor fa fa-history" aria-hidden="true" title="Show chat history"></i>
        <i id="btn-disconnect" class="connect_disconnect fa fa-plug" title="Disconnect from server"></i>
        <i id="settings" class="anchor fa fa-cog" aria-hidden="true" title="All settings"></i>
        <i id="clear_messages" class="anchor fa fa-trash-o" aria-hidden="true" title="Clear all messages"></i>
    </div>
    <div id="all_messages" class="messages"></div>
    <div class="send_message">
        <input id="send_data" class="size clearable" type="text" name="" value="" placeholder="Type your message..." autocomplete="off" />
    </div>

    <script src="../static/scripts/libs/jquery/jquery.js"></script>
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
            $('#send_data').keydown(function(event) {
                if( event.keyCode == 13 || event.which == 13 ){
                    if( click_events.is_connected ) {
                        var send_data = { };
                        send_data.data = escape( $( '#send_data' ).val() ) + ':' + utils.get_userdata();
                        socket.emit( 'event broadcast', send_data );
                        $( '#send_data' ).val('');
                    }
                    return false;
                }
            });
        },
        // event for connected and disconnect buttons
        connect_disconnect: function(socket) {
            $( '.connect_disconnect' ).click(function( event ){
                var $el = $( '.connect_disconnect' ),
                    id = $el.prop("id"),
                    send_data = { },
                    uid = utils.get_userid(),
                    $el_all_messages = $( '#all_messages' ),
                    $el_online_status = $('#online_status'),
                    $el_connect_disconnect = $('.connect_disconnect'),
                    disconnected_message = "You are disconnected and can't send/receive messages...",
                    connected_message = "You are connected again...",
                    disconnect_tooltip = "Disconnect from server",
                    connect_tooltip = "Connect to server";
                                if( id === "btn-disconnect" ) {
                    // disconnect only if connected
                    if (click_events.is_connected) {
                        send_data.data = "disconnected" + ":" + utils.get_username();
                        socket.emit( 'event disconnect', send_data );
                        sessionStorage.removeItem(uid);
                        disconnected_message = "<div class='disconn_msg'>" + disconnected_message + "</div>";
                        utils.append_message( $el_all_messages,  disconnected_message);
                        this.is_connected = false;
                        utils.update_online_status( $el_online_status, this.is_connected );
                        utils.switch_connect_disconnect( $el_connect_disconnect, "btn-connect", connect_tooltip );
                        utils.scroll_to_last( $el_all_messages );
                    }
                }
                else if ( id === "btn-connect" ) {
                // connects to socket again
                    socket.connect();
                    this.is_connected = true;
                    connected_message = "<div class='conn_msg'>" + connected_message + "<i class='fa fa-smile-o' aria-hidden='true'></i></div>";
                    utils.append_message( $el_all_messages, connected_message );
                    utils.switch_connect_disconnect( $el_connect_disconnect, "btn-disconnect", disconnect_tooltip );
                    utils.update_online_status( $el_online_status, this.is_connected );
                    // show the last item by scrolling to the end
                    utils.scroll_to_last( $el_all_messages );
                }
                return false;
            });
        },
        // clear all the messages
        clear_messages: function() {
        $( '#clear_messages' ).click(function( event ){
            // clears all the messages
                $("#all_messages").html("");
                return false;
            });
        },
        // shows full chat history
        show_chat_history: function() {
            $( '#chat_history' ).click( function( events ) {
                utils.fill_messages(localStorage[utils.get_userid()]);
            });
        }
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
        fill_messages: function ( collection ) {
            var uid = utils.get_userid(),
            message_html = $.parseHTML( collection ),
            $el_all_messages = $('#all_messages');
            // clears the previous items
            $('#all_messages').html("");
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
        append_message: function($el, message) {
            $el.append( message );
            $el.append('<br>');
        },
        // builds message
        build_message: function(original_message, uid) {
            var from_uid = original_message[1].split('-')[1],
                message_user = "",
                message_text = "";
            // for user's own messages
            if ( from_uid === uid ) {
                message_user = "<span class='user_name'> me <br> </span>"; //
            }
            // for other user's messages
            else {
                message_user = "<span class='user_name'>" + unescape(original_message[1].split('-')[0]) + "<br></span>";
            }
            message_text = "<div class='user_message'> <i class='fa fa-quote-left' aria-hidden='true'></i> " +
                unescape( original_message[0] ) + " <i class='fa fa-quote-right' aria-hidden='true'></i><div class='date_time'><span><i class='fa fa-clock-o' aria-hidden='true'></i> "+ this.get_date_time() + "</span></div></div>";
            return message_user + message_text;
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
        // switch buttons connect and disconnect
        switch_connect_disconnect: function( $el, btn_id, btn_tooltip) {
            $el.prop("id", btn_id).prop("title", btn_tooltip);
        },
        // gets the current date and time
        get_date_time: function() {
            var currentdate = new Date(),
                datetime = "",
                month = 0,
                day = 0,
                hours = 0,
                minutes = 0;
                month = ( (currentdate.getMonth()+1 ) < 10) ? ( "0" + (currentdate.getMonth()+1) ) : ( currentdate.getMonth()+1 );
                day = ( currentdate.getDate() < 10 ) ? ( "0" + currentdate.getDate() ) : currentdate.getDate();
                hours = ( currentdate.getHours() < 10 ) ? ( "0" + currentdate.getHours() ) : currentdate.getHours();
                minutes = ( currentdate.getMinutes() < 10 ) ? ( "0" + currentdate.getMinutes() ) : currentdate.getMinutes();
                datetime = month + "/"
                + day  + "/"
                + currentdate.getFullYear() + " @ "
                + hours + ":"
                + minutes;
                return datetime;
        },
        set_user_info: function() {
            $( '.user' ).prop( 'title', this.get_username() );
        }
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
            utils.update_online_status( $('#online_status'), true );
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
            click_events.show_chat_history();
            // clears all the messages
            click_events.clear_messages();
            utils.get_date_time();
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

