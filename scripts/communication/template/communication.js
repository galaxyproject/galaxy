// the namespace events connect to
var namespace = '/chat',
        socket = io.connect(window.location.protocol + '//' + document.domain + ':' + location.port + namespace),
        global_chat_rooms = ['Room1', 'Room2', 'Room3', 'Room4', 'Room5'];
// socketio events
var events_module = {
    // event handler for sent data from server
    event_response: function (socket) {
        socket.on('event response', function (msg) {
            var message = "",
                    uid = utils.get_userid(),
                    $el_all_messages = $('#all_messages'),
                    $el_tab_li = $("a[data-target='#all_chat_tab']");

            // builds the message to be displayed
            message = utils.build_message(msg);

            // append only for non empty messages
            if (msg.data.length > 0) {
                utils.append_message($el_all_messages, message);
                // adding message to build full chat history
                utils.store_append_message(uid, message);
            }
            // updates the user session storage with all the messages
            sessionStorage['broadcast'] = $el_all_messages.html();
            // show the last item by scrolling to the end
            utils.scroll_to_last($el_all_messages);
            // Alert user if needed
            if (uid !== msg.user) {
                utils.show_notification($el_tab_li);
            }
        });
    },
    // event handler for room messages
    event_response_room: function (socket) {
        socket.on('event response room', function (msg) {
            var $el_all_messages = $('#all_messages'),
                    message = {},
                    uid = utils.get_userid(),
                    tab_counter = 0,
                    $el_tab_li = null;
            // response when user joins
            if (msg.userjoin) {
                message = {
                    data: msg.userjoin + " has joined " + msg.data,
                    user: 'Server',
                };
                utils.append_message($el_all_messages, utils.build_message(message));
                utils.scroll_to_last($el_all_messages);

                if (uid !== msg.userjoin) {
                    $el_tab_li = $("a[data-target='#all_chat_tab']");
                    utils.show_notification($el_tab_li);
                }
            } // response when user leaves
            else if (msg.userleave) {
                message = {
                    data: msg.userleave + " has left " + msg.data,
                    user: 'Server',
                };
                utils.append_message($el_all_messages, utils.build_message(message));
                utils.scroll_to_last($el_all_messages);
                if (uid !== msg.userleave) {
                    $el_tab_li = $("a[data-target='#all_chat_tab']");
                    utils.show_notification($el_tab_li);
                }
            }
            else { // normal message sharing when connected
                $el_room_msg = $("#all_messages_" + msg.chatroom);
                utils.append_message($el_room_msg, utils.build_message(msg));
                utils.scroll_to_last($el_room_msg);
                // if the pushed message is for some other user, show notification
                if (uid !== msg.data) {
                    $el_tab_li = $("a[data-target='#galaxy_tabroom_" + msg.chatroom + "'" + " ]");
                    utils.show_notification($el_tab_li);
                }
            }
        });
    },
    // event handler for new connections
    event_connect: function (socket) {
        socket.on('connect', function () {
            var send_data = {};
            send_data.data = 'connected';
            socket.emit('event connect', send_data);
        });
    }
}
// all the click events of buttons
var click_events = {
    // on form load, user is connected, so the value is true
    is_connected: true,
    active_tab: "#all_chat_tab",
    connected_room: [],
    broadcast_data: function ( socket ) {
        $('#send_data').keydown(function ( e ) {
            var $el_active_li = $( '.nav-tabs>li.active' ),
                $el_send_data = $( '#send_data' ),
                message = "";
            message = $el_send_data.val();
            message = message.trim(); // removes whitespaces
            if( message.length > 0 && click_events.is_connected ) {
	        var send_data = {},
		        event_name = "";
		if ( e.keyCode == 13 || e.which == 13 ) { // if enter is pressed
		    // if the tab is all chats
		    if ( click_events.active_tab === '#all_chat_tab' ) {
		        send_data.data = message;
		        event_name = 'event broadcast';
		    }
		    else { // if the tab belongs to room
                        send_data.data = message;
		        send_data.room = $el_active_li.children().attr("title");
		        event_name = 'event room';
		    }
		    socket.emit(event_name, send_data);
		    $el_send_data.val('');
		    return false;
		}
            }
        });
    },
    // sets the current active tab
    active_element: function () {
        $('.nav-tabs>li').click(function (e) {
            if( e.target.attributes['data-target'] ) {
                click_events.active_tab = e.target.attributes['data-target'].nodeValue;
                $(this).children().css('background-color', '');
                // hides the message textarea for create room tab
                utils.show_hide_textarea( $(this).children() );
                var tab_content_id = $('.nav li.active').children().attr('data-target');
                // scroll to last in the tab content
                if( tab_content_id ) {
                    utils.scroll_to_last( $(tab_content_id) );
                }
            }
        });
    },
    // event for connected and disconneted states
    connect_disconnect: function ( socket ) {
        $('#online_status').click(function () {
            var $el_online_status = $('#online_status'),
                    $el_input_text = $('#send_data'),
                    send_data = {},
                    connected_message = 'Type your message...',
                    uid = utils.get_userid();
            if ( click_events.is_connected ) {
                click_events.make_disconnect(uid, $el_input_text, $el_online_status);
            }
            else {
                socket.connect();
                click_events.is_connected = true;
                sessionStorage['connected'] = true;
                utils.update_online_status($el_online_status, click_events.is_connected);
                $el_input_text.prop('disabled', false);
                $el_input_text.val('');
                $el_input_text.prop('placeholder', connected_message);
            }
        });
    },
    // clear all the messages
    clear_messages: function () {
        $('#clear_messages').click(function ( e ) {
            // clears all the messages
            utils.clear_message_area();
            return false;
        });
    },
    // shows full chat history
    show_chat_history: function () {
        $('#chat_history').click(function (events) {
            utils.fill_messages(localStorage[utils.get_userid()]);
        });
    },
    // delete full history
    delete_history: function () {
        $('#delete_history').click(function () {
            var uid = utils.get_userid();
            localStorage.removeItem(uid);
            sessionStorage.removeItem(uid);
            utils.clear_message_area();
        });
    },
    // makes disconnect
    make_disconnect: function (uid, $el_input_text, $el_online_status) {
        var send_data = {}
        disconnected_message = 'You are now disconnected. To send/receive messages, please connect';
        click_events.is_connected = false;
        socket.emit('event disconnect', send_data);
        sessionStorage.removeItem(uid);
        sessionStorage['connected'] = false;
        utils.update_online_status($el_online_status, click_events.is_connected);
        $el_input_text.val('');
        $el_input_text.prop('placeholder', disconnected_message);
        $el_input_text.prop('disabled', true);
    },
    // for creating/joining user created chat room
    create_chat_room: function () {
        var $el_txtbox_chat_room = $('#txtbox_chat_room'),
            $el_chat_room_tab = $('#chat_room_tab'),
            $el_chat_tabs = $('#chat_tabs'),
            $el_tab_content = $('.tab-content'),
            $el_msg_box = $('#send_data');
        $el_txtbox_chat_room.keydown(function ( e ) {
            var chat_room_name = $el_txtbox_chat_room.val();
            if ( ( e.which === 13 || e.keyCode === 13 ) && chat_room_name.length > 0 ) { // if enter is pressed
                utils.create_new_tab(chat_room_name, $el_txtbox_chat_room, $el_chat_room_tab, $el_chat_tabs, $el_tab_content, $el_msg_box);
                return false;
            }
        });
    },
    // for chat rooms/ group chat
    leave_close_room: function () {
        var tab_counter = "",
            room_name = "",
            room_index = 0;
        $('.close-room').click(function ( e ) {
            //$el_last_chat_tab = ;
            e.stopPropagation();
            // leaves room
            room_name = e.target.parentElement.title;
            socket.emit( 'leave', {room: room_name} );
            // removes tab and its content
            $( '.tab-content ' + $(this).parent().attr('data-target') ).remove();
            $(this).parent().parent().remove();
            room_index = click_events.connected_room.indexOf(room_name);
            click_events.connected_room.splice(room_index, 1);
            // selects the last tab and makes it active
            $('#chat_tabs a:last').tab('show');
            // hides or shows textarea
            utils.show_hide_textarea( $('#chat_tabs a:last') );
            // adjusts the left/right scrollers
            // when a tab is deleted
            utils.adjust_scrollers();
            return false;
        });
    },
    // registers overflow tabs left/right click events
    overflow_left_right_scroll: function() {
        var $el_scroll_right = $('.scroller-right'),
            $el_scroll_left = $('.scroller-left');
        $('.scroller-right').click(function() {
            $el_scroll_left.fadeIn('slow');
            $el_scroll_right.fadeOut('slow');
            // performs animation when the scroller is clicked
            // and shifts the tab list to the right end
            $('.list').animate({left: "+=" + utils.get_width_hidden_list() + "px"}, 'slow', function() { });
        });
        $el_scroll_left.click(function() {
            $el_scroll_right.fadeIn('slow');
            $el_scroll_left.fadeOut('slow');
            // performs animation when the scroller is clicked
            // and shifts the tab list to the left end
            $('.list').animate({left: "-=" + utils.get_list_left_position() + "px"}, 'slow', function() { });
        });
    },
    // opens a global chat room
    open_global_chat_room: function() {
        var $el_txtbox_chat_room = $('#txtbox_chat_room'),
            $el_chat_room_tab = $('#chat_room_tab'),
            $el_chat_tabs = $('#chat_tabs'),
            $el_tab_content = $('.tab-content'),
            $el_msg_box = $('#send_data'),
            chat_room_name = '';
        $('.global-room').click(function( e ) {
            e.stopPropagation();
            chat_room_name = e.target.parentElement.title;
            utils.create_new_tab( chat_room_name, $el_txtbox_chat_room, $el_chat_room_tab, $el_chat_tabs, $el_tab_content, $el_msg_box);
            return false;
        });
    },
}
// utility methods
var utils = {
    // fill in all messages
    fill_messages: function (collection) {
        var uid = utils.get_userid(),
                message_html = $.parseHTML(collection),
                $el_all_messages = $('#all_messages');
        // clears the previous items
        this.clear_message_area();
        if (collection) {
            $el_all_messages.append($('<div' + '/' + '>').html(message_html));
        }
        // show the last item by scrolling to the end
        utils.scroll_to_last($el_all_messages);
    },
    // get the current username of logged in user
    get_userid: function () {
        return location.search.split('username=')[1];
    },
    // scrolls to the last of element
    scroll_to_last: function ($el) {
        if ($el[0]) {
            $el.scrollTop($el[0].scrollHeight);
        }
    },
    // append message
    append_message: function ($el, message) {
        $el.append(message);
        $el.append('<br>');
    },
    // builds message for self
    build_message: function (original_message) {
        var from_uid = original_message.user,
                message_data = original_message.data,
                message_user = "",
                message_text = "",
                uid = utils.get_userid();

        // for user's own messages
        if (from_uid === uid) {
            message_user = this.build_message_username_template('me');
        }
        // for other user's messages
        else {
            message_user = this.build_message_username_template(from_uid);
        }
        message_text = this.build_message_template(message_data);
        return message_user + message_text;
    },
    // builds message template
    build_message_template: function (original_message) {
        return "<div class='user_message'>" + unescape(original_message) +
                "<div class='date_time'><span title=" + this.get_date() + ">" + this.get_time() + "</span>" +
                "</div></div>";
    },
    // builds template for username for message display
    build_message_username_template: function (username) {
        return "<span class='user_name'>" + username + "<br></span>";
    },
    // adds an information about the online status
    update_online_status: function ($el, connected) {
        if (connected) {
            $el.prop("title", "You are online! Press to be offline.").css("color", "#00FF00");
        }
        else {
            $el.prop("title", "You are offline! Press to be online.").css( "color", "#FF0000");
        }
    },
    // gets the current time
    get_time: function () {
        var currentdate = new Date(),
                datetime = "",
                hours = 0,
                minutes = 0;
        hours = ( currentdate.getHours() < 10 ) ? ( "0" + currentdate.getHours() ) : currentdate.getHours();
        minutes = ( currentdate.getMinutes() < 10 ) ? ( "0" + currentdate.getMinutes() ) : currentdate.getMinutes();
        datetime = hours + ":" + minutes;
        return datetime;
    },
    // gets the current date
    get_date: function () {
        var currentdate = new Date(),
                day,
                month;
        month = ( (currentdate.getMonth() + 1 ) < 10) ? ( "0" + (currentdate.getMonth() + 1) ) : ( currentdate.getMonth() + 1 );
        day = ( currentdate.getDate() < 10 ) ? ( "0" + currentdate.getDate() ) : currentdate.getDate();
        return month + "/" + day + "/" + currentdate.getFullYear();
    },
    // clears the message list
    clear_message_area: function () {
        $('#all_messages').html("");
    },
    // shows notification when a message is
    // pushed to the inactive tab
    show_notification: function ($el) {
        if (!$el.parent().hasClass('active')) {
            $el.css('background-color', '#FCD116');
            for (var i = 2; i >= 1; i--) {
                $el.fadeOut(200).fadeIn(200);
            }
        }
    },
    // adjusts the scrollers when a
    // tab is added or deleted
    adjust_scrollers: function() {
        if ( $('.wrapper').width() < this.get_list_width() ) {
            $('.scroller-right').show();
        }
        else {
            $('.scroller-right').hide();
        }

        if (this.get_list_left_position() < 0) {
            $('.scroller-left').show();
        }
        else {
            $('.item').animate( {left: "-=" + this.get_list_left_position() + "px"}, 'slow' );
            $('.scroller-left').hide();
        }
    },
    // gets the widht of all li elements
    get_list_width: function() {
        var total_width = 0;
        $('.list li').each(function() {
            var li_width = $(this).width();
            total_width += li_width;
        });
        return total_width;
    },
    // gets the hidden width of the tab
    get_width_hidden_list: function() {
        var scroll_icon_width = 50;
        return ( $('.wrapper').width() - this.get_list_width() - this.get_list_left_position() - scroll_icon_width );
    },
    get_list_left_position: function() {
        return $('.list').position().left;
    },
    // checks the session storage on page load
    checks_session_storage: function() {
        var uid = utils.get_userid();
        if (sessionStorage['connected']) {
            if (sessionStorage['connected'] === 'true' || sessionStorage['connected'] === true) {
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
    },
    // show/hide textarea message box
    show_hide_textarea: function( $selector ) {
         if ( $selector.attr("data-target") === "#chat_room_tab" ) {
             $('#send_data').css('display', 'none');
         }
         else {
             $('#send_data').css('display', 'block');
         }
    },
    store_append_message: function( key, data ) {
        if (!localStorage[key]) {
            localStorage[key] = data + '<br>';
        }
        else {
            localStorage[key] = localStorage[key] + data + '<br>';
        }
        //sessionStorage[key] = localStorage[key];
    },
    create_global_chatroom_links: function() {
        // global_rooms
        var $el_room_container = $('#global_rooms'),
            room_name = "",
            room_template = "";
        //$el_room_container.html('');
        for(var room_counter = 0; room_counter < global_chat_rooms.length; room_counter++ ) {
            room_name = global_chat_rooms[room_counter];
            room_template = "<a href='#' class='global-room' title=" + room_name + "><span>" + room_name + "</span></a><br>";
            $el_room_container.append(room_template);
        }
    },
    // creates a new tab and joins a chat room
    create_new_tab: function( chat_room_name, $el_txtbox_chat_room, $el_chat_room_tab, $el_chat_tabs, $el_tab_content, $el_msg_box) {
        var self = click_events,
            tab_room_header_template = "",
            tab_room_body_template = "",
            tab_id = "",
            $el_active_li = $('ul>li.active');
        // checks if the room is already open and displays it if open
        // otherwise create a new one
        if(self.connected_room.indexOf(chat_room_name) > -1) {
            $el_chat_tabs.find( "a[title='" + chat_room_name + "']" ).tab('show');
        }
        else {
            // emits join room event
            socket.emit('join', {room: chat_room_name});
	    // removes the active class from the chat creating tab
	    $el_chat_room_tab.removeClass('fade active in').addClass('fade');
	    $el_active_li.removeClass('active');
	    // sets new tab id
            tab_id = "galaxy_tabroom_" + chat_room_name;
            self.connected_room.push( chat_room_name );
	    // create chat room tab header for new room
	    tab_room_header_template = "<li class='active'><a title=" + chat_room_name + " data-target=" + "#" + tab_id +
		               " data-toggle='tab' aria-expanded='false'>" + chat_room_name +
		               "<i class='fa fa-times anchor close-room' title='Close room'></i></a></li>";
	    $el_chat_tabs.append( tab_room_header_template );
	    // create chat room tab body for new room
	    tab_room_body_template = "<div class='tab-pane active fade in' id=" + tab_id +
		             "><div id='all_messages_" + chat_room_name + "'" + " class='messages'></div></div>";
	    $el_tab_content.append(tab_room_body_template);
            // registers leave room event
	    self.leave_close_room();
        }
        self.active_element();
        // displays the textarea
	$el_msg_box.css('display', 'block');
        $el_txtbox_chat_room.val("");
        // adjusts the left/right scrollers when a tab is created
	utils.adjust_scrollers();
    },
}

// registers the events when this document is ready
$(document).ready(function () {
    // fill the messages if user is already connected
    // and comes back to the chat window
    var uid = utils.get_userid();

    // registers response event
    events_module.event_response(socket);
    // registers room response event
    events_module.event_response_room(socket);
    // registers connect event
    events_module.event_connect(socket);

    // registers create room event
    click_events.create_chat_room(socket);
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
    click_events.active_element();
    click_events.leave_close_room();
    // register tab overflow scroll events
    click_events.overflow_left_right_scroll();

    // build tabs
    $('#chat_tabs').tab();
    $('#send_data').val("");
    utils.fill_messages(sessionStorage['broadcast']);
    // updates online status text
    // by checking if user was connected or not
    utils.checks_session_storage();
    utils.scroll_to_last($('#all_messages'));
    // create global chat rooom links and
    // registers their click events
    utils.create_global_chatroom_links();
    click_events.open_global_chat_room();
});
