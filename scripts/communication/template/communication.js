// the namespace chat events connect to
var namespace = '/chat',
    socket = io.connect(window.location.protocol + '//' + document.domain + ':' + location.port + namespace);

// socketio events
var events_module = {
    // event handler for sent data from server
    event_response: function (socket) {
        socket.on('event response', function ( msg ) {
            var message = "",
                uid = utils.get_userid(),
                $el_all_messages = $( '#all_messages' ),
                $el_tab_li = $( "a[data-target='#all_chat_tab']" );

            // builds the message to be displayed
            message = utils.build_message( msg );
            
            // append only for non empty messages
            if (msg.data.length > 0) {
                utils.append_message( $el_all_messages, message );
                utils.vertical_center_align_gravatar( $( '#all_messages .message' ) );
                // adding message to build full chat history
                utils.store_append_message( uid, $el_all_messages.html() );
            }
            // updates the user session storage with all the messages
            sessionStorage[uid] = $el_all_messages.html();
            // show the last item by scrolling to the end
            utils.fancyscroll_to_last( $("#all_chat_tab") );
            // Alert user if needed
            if ( uid !== msg.user ) {
                utils.show_notification( $el_tab_li );
            }
        });
    },
    // event handler for room messages
    event_response_room: function (socket) {
        socket.on('event response room', function ( msg ) {
            var $el_all_messages = $( '#all_messages' ),
                    message = {},
                    uid = utils.get_userid(),
                    tab_counter = 0,
                    $el_tab_li = null,
                    server_text_name = 'Notification';
            // response when user joins
            if (msg.userjoin) {
                message = {
                    data: msg.userjoin + " has joined " + msg.data,
                    user: server_text_name,
                };
                utils.append_message( $el_all_messages, utils.build_message( message ) );
                utils.fancyscroll_to_last( $("#all_chat_tab") );
                // shows notification when message is from other user
                if ( uid !== msg.userjoin ) {
                    $el_tab_li = $( "a[data-target='#all_chat_tab']" );
                    utils.show_notification( $el_tab_li );
                }
            } // response when user leaves
            else if ( msg.userleave ) {
                message = {
                    data: msg.userleave + " has left " + msg.data,
                    user: server_text_name,
                };
                utils.append_message( $el_all_messages, utils.build_message( message ) );
                utils.fancyscroll_to_last( $("#all_chat_tab") );
                // shows notification when message is from other user
                if ( uid !== msg.userleave ) {
                    $el_tab_li = $( "a[data-target='#all_chat_tab']" );
                    utils.show_notification( $el_tab_li );
                }
            }
            else { // normal message sharing when connected
                var room = utils.check_room_by_roomname( click_events.connected_room, msg.chatroom );
                $el_room_msg = $( '#all_messages_' + room.id );
                utils.append_message( $el_room_msg, utils.build_message( msg ) );
                utils.vertical_center_align_gravatar( $( '#all_messages_' + room.id + ' .message' ) );
                utils.fancyscroll_to_last( $( "#galaxy_tabroom_" + room.id ) );
                // if the pushed message is for some other user, show notification
                if (uid !== msg.data) {
                    $el_tab_li = $( "a[data-target='#galaxy_tabroom_" + room.id + "'" + " ]" );
                    utils.show_notification( $el_tab_li );
                }
            }
        });
    },
    // event handler for new connections
    event_connect: function ( socket ) {
        socket.on('connect', function () {
            var send_data = {};
            send_data.data = 'connected';
            socket.emit( 'event connect', send_data );
        });
    }
}
// all the click events of buttons
var click_events = {
    // on form load, user is connected, so the value is true
    is_connected: true,
    active_tab: "#all_chat_tab",
    connected_room: [],
    tab_counter : 0,
    broadcast_data: function ( socket ) {
        $('#send_data').keydown(function ( e ) {
            var $el_active_li = $( '.nav-tabs>li.active' ),
                $el_send_data = $( '#send_data' ),
                message = "";
            message = $el_send_data.val();
            message = message.trim(); // removes whitespaces
            // return false if entered is pressed without any message
            if( message.length == 0 && ( e.keyCode == 13 || e.which == 13 ) ) {
                return false;
            }
            if( click_events.is_connected ) {
            var send_data = {},
                event_name = "";
                if ( e.keyCode == 13 || e.which == 13 ) { // if enter is pressed
                    // if the tab is all chats
                    if ( click_events.active_tab === '#all_chat_tab' ) {
                        send_data.data = message;
                        event_name = 'event broadcast';
                    }
                    else { // if the tab belongs to a room
                        send_data.data = message;
                        send_data.room = $el_active_li.children().attr( "title" );
                        event_name = 'event room';
                    }
                    socket.emit( event_name, send_data );
                    $el_send_data.val('');
                    return false;
                }
            }
        });
    },
    // sets the current active tab
    active_element: function () {
        $('.nav-tabs>li').click(function ( e ) {
            var tab_content_id = null,
                message_area_div_id = "",
                message_area_id = "",
                $el_create_textbox = $('#txtbox_chat_room');
            if( e.target.attributes['data-target'] ) {
                // sets the active tab
                click_events.active_tab = e.target.attributes['data-target'].nodeValue;
                // removes the background color
                $( this ).children().css( 'background-color', '' );
                // hides the message textarea for create room tab
                utils.show_hide_textarea( $( this ).children() );
                // finds the tab content and scrolls to last
                message_area_div_id = $( this ).find('a').attr( 'data-target' );
                if( message_area_div_id ) { // if it has message area
                    utils.fancyscroll_to_last( $( message_area_div_id ) );
                }
            }
        });
    },
    create_room: function() {
       $(".create-room").click(function( e ) {
           // create global chat rooom links and
           // registers their click events
           $( ".global-rooms" ).html( "" );
           utils.create_global_chatroom_links();
           click_events.open_global_chat_room();
       });
    },
    // event for connected and disconneted states
    // toggles the connection status icon
    connect_disconnect: function ( socket ) {
        $('#online_status').click(function () {
            var $el_online_status = $( '#online_status' ),
                    $el_input_text = $( '#send_data' ),
                    send_data = {},
                    connected_message = 'Type your message...',
                    uid = utils.get_userid();
            if ( click_events.is_connected ) { // if connected, disconnect
                click_events.make_disconnect( uid, $el_input_text, $el_online_status );
            }
            else { // if disconnected, reconnect
                socket.connect();
                click_events.is_connected = true;
                sessionStorage['connected'] = true;
                utils.update_online_status( $el_online_status, click_events.is_connected );
                $el_input_text.prop( 'disabled', false );
                $el_input_text.val('');
                $el_input_text.prop( 'placeholder', connected_message );
            }
        });
    },
    // shows full chat history
    show_chat_history: function () {
        $('#chat_history').click(function ( e ) {
            utils.fill_messages( localStorage[ utils.get_userid() ] );
        });
    },
    // makes disconnect and raises disconnect event at the server
    make_disconnect: function ( uid, $el_input_text, $el_online_status ) {
        var send_data = {}
        disconnected_message = 'You are now disconnected. To send/receive messages, please connect';
        click_events.is_connected = false;
        socket.emit( 'event disconnect', send_data );
        sessionStorage.removeItem( uid );
        sessionStorage[ 'connected' ] = false;
        utils.update_online_status( $el_online_status, click_events.is_connected );
        $el_input_text.val( '' );
        $el_input_text.prop( 'placeholder', disconnected_message );
        $el_input_text.prop( 'disabled', true );
    },
    // for creating/joining user created chat room
    create_chat_room: function () {
        var $el_txtbox_chat_room = $( '#txtbox_chat_room' ),
            $el_chat_room_tab = $( '#chat_room_tab' ),
            $el_chat_tabs = $( '#chat_tabs' ),
            $el_tab_content = $( '.tab-content' ),
            $el_msg_box = $( '#send_data' );
        $el_txtbox_chat_room.keydown(function ( e ) {
            var chat_room_name = $el_txtbox_chat_room.val();
            if ( ( e.which === 13 || e.keyCode === 13 ) && chat_room_name.length > 0 ) { // if enter is pressed
                chat_room_name = chat_room_name.trim(); // removes the leading and trailing whitespaces
                utils.create_new_tab( chat_room_name, $el_txtbox_chat_room, $el_chat_room_tab, $el_chat_tabs, $el_tab_content, $el_msg_box );
                $el_txtbox_chat_room.val( "" ) // clears create room textbox
                return false;
            }
        });
    },
    // for chat rooms/ group chat
    leave_close_room: function () {
        var tab_counter = "",
            room_name = "",
            room_index = 0,
            self = click_events;
        $('.close-room').click(function ( e ) {
            e.stopPropagation();
            // gets room name from the title of anchor tag
            room_name = e.target.parentElement.title;
            // leaves room
            socket.emit( 'leave', { room: room_name } );
            // removes tab and its content
            $( '.tab-content ' + $( this ).parent().attr( 'data-target' ) ).remove();
            $( this ).parent().parent().remove();
            room_index = utils.delete_from_rooms( self.connected_room, room_name );
            delete self.connected_room[ room_index ];
            // selects the last tab and makes it active
            $('#chat_tabs a:last').tab( 'show' );
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
            $('.list').animate( {left: "+=" + utils.get_width_hidden_list() + "px"}, 'slow', function() { } );
        });
        $el_scroll_left.click(function() {
            $el_scroll_right.fadeIn('slow');
            $el_scroll_left.fadeOut('slow');
            // performs animation when the scroller is clicked
            // and shifts the tab list to the left end
            $('.list').animate( {left: "-=" + utils.get_list_left_position() + "px"}, 'slow', function() { } );
        });
    },
    // opens a global chat room
    open_global_chat_room: function() {
        var $el_txtbox_chat_room = $( '#txtbox_chat_room' ),
            $el_chat_room_tab = $( '#chat_room_tab' ),
            $el_chat_tabs = $( '#chat_tabs' ),
            $el_tab_content = $( '.tab-content' ),
            $el_msg_box = $( '#send_data' ),
            chat_room_name = '';
        // creates a tab for persistent chat room upon clicking
        $('.global-room').click(function( e ) {
            e.stopPropagation();
            chat_room_name = $(this)[0].title;
            utils.create_new_tab( chat_room_name, $el_txtbox_chat_room, $el_chat_room_tab, $el_chat_tabs, $el_tab_content, $el_msg_box );
            return false;
        });
    },
    // deletes chat log on keypress ctrl + l
    // for the active chat window
    delete_chat: function() {
        $(document).keydown(function( e ) {
             var message_area_div_id = "",
                 message_area_id = "",
                 $el_active_li = $( '.nav-tabs>li.active' );
            // detects keypress of ctrl+l
            if ( ( e.which == 76 || e.keyCode == 76 ) && e.ctrlKey ) {
                message_area_div_id = $el_active_li.find('a').attr( 'data-target' );
                if( message_area_div_id === "#all_chat_tab" ) {
                    // deletes log for the main chat tab
                    $('#all_chat_tab').find('#all_messages').html('');
                }
                else {
                    // deletes log for the other tabs
                    message_area_id = $( message_area_div_id + ' .messages' ).attr( 'id' );
                    if( message_area_id ) { // deletes the chat log
                        utils.clear_message_area( $( '#' + message_area_id ) );
                    }
                }
            }
        });
    },
    // event for body resize
    event_window_resize: function() {
        $( window ).resize(function() {
            var body_width = $('.body-container').width();
            if ( body_width > 600 ) {
                $('.right_icons').css('margin-left', '97%');
                $('.tab-content').height( '79%' );
            }
            else {
                $('.right_icons').css('margin-left', '95%');
                $('.tab-content').height( '65%' );
            }
            // adjusts the vertical alignment of the gravatars
            utils.gravatar_align();
            
        });
    }
}
// utility methods
var utils = {
    notification_color_code: '#FFD700',
    connected_color_code: "#00FF00",
    disconnected_color_code: "#FF0000",
    // fill in all messages
    fill_messages: function ( collection ) {
        var uid = utils.get_userid(),
            message_html = $.parseHTML( collection ),
            $el_all_messages = $( '#all_messages' );
        // clears the previous items
        this.clear_message_area( $el_all_messages );
        if ( collection ) {
            $el_all_messages.append( $( '<div' + '/' + '>' ).html( message_html ) );
        }
        // show the last item by scrolling to the end
        utils.fancyscroll_to_last( $("#all_chat_tab") );
        utils.gravatar_align();
    },
    // get the current username of logged in user
    get_userid: function () {
        var query_string_start = location.search.indexOf( '?' ) + 1,
            query_string_list = location.search.slice( query_string_start ).split( '&' );
        return query_string_list[0].split( '=' )[1];
    },
    // append message
    append_message: function ( $el, message ) {
        $el.append( message );
    },
    // builds message for self
    build_message: function ( original_message ) {
        var from_uid = original_message.user,
            message_data = original_message.data,
            message_user = "",
            message_text = "",
            uid = utils.get_userid();

        var user = {
            username: original_message.user,
            gravatar: original_message.gravatar,
        }

        if (from_uid === uid) {
            // for our own user we override the text_name
            user.username = "me";
        }

        return this.build_message_from_template( user, message_data );
    },
    // builds template for message display
    build_message_from_template: function ( user, original_message ) {
        var gravatar_col_content = '' +
               '<img src="https://s.gravatar.com/avatar/' + user.gravatar + '?s=32&d=identicon" />' +
               '';

        var message_col_content = '<div class="row">'+
            '   <div class="col-xs-6 user_name">' +
                    user.username +
            '   </div>' +
            '   <div class="col-xs-6 text-right date_time" title="'+ this.get_date() +'">' +
                    this.get_time() +
            '   </div>' +
            '</div>' +
            '<div class="row user_message">' +
                unescape( original_message ) +
            '</div>';
        if ( user.username === "me" ){
            return '<div class="row message">' +
            '<div class="col-xs-11 col-md-12 message-height">' +
                message_col_content +
            '</div>' +
            '<div class="col-xs-1 col-md vertical-align">' +
                gravatar_col_content +
            '</div>' +
            '</div>';
        } else if ( user.username === "Notification" ){
            return '<div class="row message">' +
            '<div class="col-xs-11 col-md-12 notification-padding">' +
                message_col_content +
            '</div>' +
            '</div>';
        } else {
            return '<div class="row message">' +
            '<div class="col-xs-1 col-md vertical-align">' +
                gravatar_col_content +
            '</div>' +
            '<div class="col-xs-11 col-md-12 message-height">' +
                message_col_content +
            '</div>' +
            '</div>';
        }
    },
    // adds an information about the online status
    update_online_status: function ( $el, connected ) {
        var connected_message = "You are online. Press to be offline.",
            disconnected_message = "You are offline. Press to be online.";
        if ( connected ) {
            $el.prop( "title", connected_message ).css( "color", this.connected_color_code );
        }
        else {
            $el.prop( "title", disconnected_message ).css( "color", this.disconnected_color_code );
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
        month = ( (currentdate.getMonth() + 1 ) < 10) ? ( "0" + ( currentdate.getMonth() + 1 ) ) : ( currentdate.getMonth() + 1 );
        day = ( currentdate.getDate() < 10 ) ? ( "0" + currentdate.getDate() ) : currentdate.getDate();
        return month + "/" + day + "/" + currentdate.getFullYear();
    },
    // clears the message area or chat logs
    // from the currently active tab
    clear_message_area: function ( $el ) {
        $el.html( "" );
    },
    // shows notification and animating when a message is being
    // pushed to an inactive tab(s)
    show_notification: function ( $el ) {
        if ( !$el.parent().hasClass( 'active' ) ) {
            $el.css( 'background-color', this.notification_color_code );
            for (var i = 2; i >= 1; i--) {
                // shows the animation
                $el.fadeOut( 150 ).fadeIn( 150 );
            }
        }
    },
    // adjusts the scrollers when a
    // tab is added or deleted
    adjust_scrollers: function() {
        if ( $( '.wrapper' ).width() < this.get_list_width() ) {
            $( '.scroller-right' ).show();
        }
        else {
            $( '.scroller-right' ).hide();
        }

        if ( this.get_list_left_position() < 0 ) {
            $( '.scroller-left' ).show();
        }
        else {
            $( '.item' ).animate( {left: "-=" + this.get_list_left_position() + "px"}, 'slow' );
            $( '.scroller-left'  ).hide();
        }
    },
    // gets the widht of all li elements
    get_list_width: function() {
        var total_width = 0;
        $( '.list li' ).each(function() {
            var li_width = $( this ).width();
            total_width += li_width;
        });
        return total_width;
    },
    // gets the hidden width of the tab
    get_width_hidden_list: function() {
        var scroll_icon_width = 50;
        return ( $( '.wrapper' ).width() - this.get_list_width() - this.get_list_left_position() - scroll_icon_width );
    },
    get_list_left_position: function() {
        return $( '.list' ).position().left;
    },
    // checks the session storage on page load
    // and updates connected status
    checks_session_storage: function() {
        var uid = utils.get_userid(),
            $el_all_messages = $( '#all_messages' ),
            $el_online_status = $( '#online_status' ),
            $el_textarea = $( '#send_data' );
        if ( sessionStorage[ 'connected' ] ) {
            if ( sessionStorage[ 'connected' ] === 'true' || sessionStorage[ 'connected' ] === true ) {
                utils.update_online_status( $el_online_status, true );
                click_events.is_connected = true;
            }
            else {
                click_events.make_disconnect( uid, $el_textarea, $el_online_status );
                utils.clear_message_area( $el_all_messages );
            }
        }
        else {
            utils.update_online_status( $el_online_status, true );
            click_events.is_connected = true;
        }
    },
    // show/hide textarea message box
    show_hide_textarea: function( $selector ) {
         var $el_textarea = $( '#send_data' );
         if ( $selector.attr( "data-target" ) === "#chat_room_tab" ) {
             $el_textarea.css( 'display', 'none' );
         }
         else {
             $el_textarea.css('display', 'block');
             utils.set_focus_textarea( $el_textarea );
         }
    },
    // save chat logs
    store_append_message: function( key, data ) {
        localStorage[key] = data;
    },
    create_global_chatroom_links: function() {
        // global_rooms
        var $el_room_container = $('#global_rooms'),
            room_name = "",
            room_template = "",
            persistent_communication_rooms = [],
            persistent_rooms_length = 0,
            $el_persistent_rooms_visible = $(".persistent-rooms-visibility");
        // gets an array of persistent communication rooms
        persistent_communication_rooms = this.get_persistent_rooms();
        persistent_rooms_length = persistent_communication_rooms.length;
        if( persistent_rooms_length > 0 ) {
            $el_persistent_rooms_visible.css('display', 'block');
            // creates html template for persistent rooms
            for(var room_counter = 0; room_counter < persistent_rooms_length; room_counter++ ) {
                room_name = persistent_communication_rooms[room_counter];
                room_template = "<button type='button' class='btn btn-primary global-room' title='" + room_name +
                                "'>" + room_name + "</button>";
                $el_room_container.append(room_template);
            }
        }
        else {
            $el_persistent_rooms_visible.css('display', 'none');
        }
    },
    // creates a new tab and joins a chat room
    create_new_tab: function( chat_room_name, $el_txtbox_chat_room, $el_chat_room_tab, $el_chat_tabs, $el_tab_content, $el_msg_box) {
        var self = click_events,
            tab_room_header_template = "",
            tab_room_body_template = "",
            tab_id = "",
            message_area_id = "",
            $el_active_li = $('ul>li.active'),
            $el_textarea = $('#send_data'),
            is_room = utils.check_room_by_roomname( self.connected_room, chat_room_name);
        // checks if the room is already open and displays it if open
        // otherwise create a new one
        if( is_room ) {
            $el_chat_tabs.find( "a[data-target='#galaxy_tabroom_" + is_room.id + "']" ).tab('show');
        }
        else {
            // emits join room event
            socket.emit('join', {room: chat_room_name});
            // removes the active class from the chat creating tab
            $el_chat_room_tab.removeClass('fade active in').addClass('fade');
            $el_active_li.removeClass('active');
            // create tab and message area ids for the
            // new tab header and tab content elements
            tab_id = "galaxy_tabroom_" + self.tab_counter;
            message_area_id = "all_messages_" + self.tab_counter;
            self.connected_room.push({
                id: self.tab_counter,
                name: chat_room_name
            });
            // create chat room tab header for new room
            tab_room_header_template = "<li class='active'><a title='" + chat_room_name + "' data-target='#" + tab_id +
                       "' data-toggle='tab' aria-expanded='false'>" + chat_room_name +
                       "<i class='fa fa-times anchor close-room' title='Close room'></i></a></li>";
            $el_chat_tabs.append( tab_room_header_template );
            // create chat room tab body for new room
            tab_room_body_template = "<div class='tab-pane active fade in' id='" + tab_id +
                       "'><div id='" + message_area_id + "'" + " class='messages'></div></div>";
            $el_tab_content.append(tab_room_body_template);
            // registers leave room event
            self.leave_close_room();
            utils.create_fancy_scroll( $( '#' + tab_id ), "#"+tab_id );
            click_events.tab_counter++;
        }
        self.active_element();
        // displays the textarea
        $el_msg_box.css('display', 'block');
        utils.set_focus_textarea( $el_textarea );
        // adjusts the left/right scrollers when a tab is created
        utils.adjust_scrollers();
    },
    // returns persistent communication rooms from the iframe url
    get_persistent_rooms: function() {
        var query_string_start = location.search.indexOf('?') + 1,
            query_string_list = location.search.slice(query_string_start).split('&'),
            persistent_rooms_list = [];
        if( query_string_list[1] ) {
            // unescapes the list
            query_string_list = unescape(query_string_list[1]);
            persistent_rooms_list = query_string_list.split('=')[1];
            if( persistent_rooms_list && persistent_rooms_list.length > 0 ) {
                return query_string_list.split('=')[1].split(',');
            }
            else {
                return [];
            }
        }
        else {
            return [];
        }
    },
    // returns the room information if it exists
    check_room_by_roomname: function( dictionary, room_name ) {
        for(var ctr = 0; ctr < dictionary.length; ctr++) {
            if( dictionary[ctr] ) {
                if( room_name === dictionary[ctr].name ) {
                    return dictionary[ctr];
                }
            }
        }
    },
    // returns the index of the room to be deleted
    // from the connected room list if the room is left by the user
    delete_from_rooms: function( dictionary, item ) {
        for(var ctr = 0; ctr < dictionary.length; ctr++) {
            if( dictionary[ctr] ) {
                if( item === dictionary[ctr].name ) {
                    return ctr;
                }
            }
        }
    },
    // sets focus inside the textarea and clears it too
    set_focus_textarea: function( $el ) {
        $el.val("");
        $el.focus();
    },
    // smooth transition of body element upon first load
    load_transition: function() {
        $('.body-container').addClass('body-container-loaded');
    },
    // creates fancy scroll for the messages area
    create_fancy_scroll: function( $el, element_id ) {
        $el.mCustomScrollbar({
            theme:"minimal"
        });
        $( element_id + ' .mCSB_dragger_bar' ).css( 'background-color', 'black' );
    },
    // scrolls the fancy scroll to the last element
    fancyscroll_to_last: function( $el ) {
        $el.mCustomScrollbar( "scrollTo", "bottom" );
    },
    // vertically aligns the gravatar icon in the center
    vertical_center_align_gravatar: function( $el ) {
        var usermsg_length = $el.find('.message-height').length,
            usermsg_height = ( $( $el.find('.message-height')[ usermsg_length - 1 ] ).height() / 2 ),
            gravatar_height = ( $( $el.find( '.vertical-align img' )[0] ).height() / 2 );

        if( gravatar_height === 0 ) {
            gravatar_height = 16;
        }	
        $( $el.find( '.vertical-align img' )[ usermsg_length - 1 ] ).css( 'padding-top', usermsg_height - gravatar_height );
    },
    
    gravatar_align: function() {
        var active_tab_target = $('li.active a').attr('data-target').split('_'),
            tab_number = "",
            selector = "", 
            scroll_selector = "",
            usermsg_height = 0,
            gravatar_height = 0;
        // finds the active tab's suffix number
        tab_number = active_tab_target[active_tab_target.length - 1];
        if( isNaN( tab_number ) ) {
            selector = "#all_messages";
            scroll_selector = "#all_chat_tab";
        }
        else {
            selector = "#all_messages_" + tab_number;
            scroll_selector = "#galaxy_tabroom_" + tab_number;
        }
        $( selector + ' .message' ).each(function( index ) {
            usermsg_height = ( $( this ).find( '.message-height' ).height() / 2 ),
            gravatar_height = ( $( this ).find( '.vertical-align img' ).height() / 2 );
            $( this ).find( '.vertical-align img' ).css( 'padding-top', (usermsg_height - gravatar_height) );
        });
        // scrolls to the last element
        utils.fancyscroll_to_last( $( scroll_selector ) );
    }
    
}
// this event fires when all the resources of the page
// have been loaded
$(window).load(function() {
    var uid = utils.get_userid(),
        $el_textarea = $('#send_data'),
        $el_all_messages = $('#all_messages'),
        $el_chat_tabs = $('#chat_tabs'),
        main_tab_id = "#all_chat_tab",
        $el_persistent_rooms_visible = $(".persistent-rooms-visibility");
    // build tabs
    $el_chat_tabs.tab();
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
    // registers event for showing chat log
    click_events.show_chat_history();
    click_events.active_element();
    click_events.leave_close_room();
    // register tab overflow scroll events
    click_events.overflow_left_right_scroll();
    // registers event for creating persistent rooms
    click_events.create_room();
    // registers event for deleting chat log
    click_events.delete_chat();
    // updates online status text
    // by checking if user was connected or not
    utils.checks_session_storage();
    utils.fill_messages(sessionStorage[uid]);
    // sets focus to the textarea
    utils.set_focus_textarea( $el_textarea );
    // sets smooth transition
    utils.load_transition();
    utils.create_fancy_scroll( $( main_tab_id ), main_tab_id );
    // scrolls to the last of the element
    utils.fancyscroll_to_last( $( main_tab_id ) );
    $el_persistent_rooms_visible.css('display', 'none');
    click_events.event_window_resize();
});
