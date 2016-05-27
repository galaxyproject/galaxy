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
    <script src="https://use.fontawesome.com/89a733ecb7.js"></script>
    <style>
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
		height: 30px;
                width: 790px;
		margin-bottom:5px;
		
	} 

        /* Styles for top right icons */
        .right_icons {
                margin: 0px 0px 10px 780px;
	}  

        #clear_messages{
		cursor: pointer;	
	}

        .messages {
		overflow: auto; 
		height: 330px;
	}

        .send_message{
		margin-top:5px;
	}
  
    </style>
</head>
<body style="overflow: hidden";> 
    <div class="right_icons">
    	<i id="online_status" class="fa fa-circle" aria-hidden="true" style="" title=""></i>
    	<i id="clear_messages" class="fa fa-eraser" aria-hidden="true" title="Clear all messages"></i>
    </div>
    <div id="all_messages" class="messages"></div>
    <div class="send_message">
	    <form id="broadcast" method="POST" action='#'>
		<input id="send_data" class="size clearable" type="text" name="" value="" placeholder="type your message..." autocomplete="off" />
		<button id="btn-send" type="submit" title="Send message">
			<i class="icon fa fa fa-paper-plane"></i>&nbsp;<span class="title">Send Message</span>
		</button>
                <button id="btn-disconnect" type="submit" title="Disconnect from server" class="connect_disconnect">
			<i class="icon fa fa fa-stop"></i>&nbsp;<span class="title">Disconnect</span>
		</button>
		<!-- <button id="btn-connect" type="submit" title="Connect again" >
			<i class="icon fa fa fa-play"></i>&nbsp;<span class="title">Re-connect</span>
		</button> -->
	    </form>
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
			$( '#btn-send' ).click( function( event ) {
                                // send data only when connected
                                if( click_events.is_connected ) {
					var send_data = { };
					send_data.data = escape( $( '#send_data' ).val() ) + ':' + utils.get_userdata();
					socket.emit( 'event broadcast', send_data );
					$( '#send_data' ).val('');
				}
				return false;
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
				    connect_tooltip = "Connect again";
                                if( id === "btn-disconnect" ) {
					// disconnect only if connected
					if (click_events.is_connected) {
						send_data.data = "disconnected" + ":" + utils.get_username();
						socket.emit( 'event disconnect', send_data );
						sessionStorage.removeItem(uid);
						utils.append_message( $el_all_messages,  disconnected_message);
				                this.is_connected = false;
						utils.update_online_status( $el_online_status, this.is_connected );
		  utils.switch_connect_disconnect( $el_connect_disconnect, "btn-connect", "Re-connect", "fa-play", "fa-stop", connect_tooltip );
		                                //$el, btn_id, btn_text, fa_class_add, fa_class_remove, btn_tooltip
		                                utils.scroll_to_last( $el_all_messages );
					}
				}
				else if ( id === "btn-connect" ) {
		                        socket.connect();
		                        this.is_connected = true;
					utils.append_message( $el_all_messages, connected_message );
	utils.switch_connect_disconnect( $el_connect_disconnect, "btn-disconnect", "Disconnect", "fa-stop", "fa-play",  disconnect_tooltip);
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
				$all_messages.append( $( '<div' + '/' + '>' ).html( message_html ) );
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
				return "me" + ": " + unescape(original_message[0]);
			}
			else {
				return unescape(original_message[1].split('-')[0]) + ": " + unescape(original_message[0]);
			}
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
		switch_connect_disconnect: function( $el, btn_id, btn_text, fa_class_add, fa_class_remove, btn_tooltip) {
                        $el.prop("id", btn_id).prop("title", btn_tooltip);
                        $el.find('i').removeClass(fa_class_remove).addClass(fa_class_add);
			$el.find('span').text(btn_text);
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
		click_events.connect_disconnect(socket);

                //click_events.connect(socket);
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

