<%inherit file="/base.mako"/>

<% is_admin = cntrller == 'admin' and trans.user_is_admin() %>

<%def name="render_user_info()">

    <script type="text/javascript">
        $(document).ready(function() {

            function validateString(test_string, type) { 
                var mail_re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
                var username_re = /^[a-z0-9\-]{4,255}$/;
                if (type === 'email') {
                    return mail_re.test(test_string);
                } else if (type === 'username'){
                    return username_re.test(test_string);
                }
            } 

            function renderError(message) {
                $(".donemessage").hide();
                if ($(".errormessage").length === 1) {
                    $(".errormessage").html(message);
                } else {
                    var div = document.createElement( "div" );
                    div.className = "errormessage";
                    div.innerHTML = message;
                    document.body.insertBefore( div, document.body.firstChild );
                    }
                }
            function renderDone(message) {
                $(".errormessage").hide();
                if ($(".donemessage").length === 1) {
                    $(".donemessage").html(message);
                } else {
                    var div = document.createElement( "div" );
                    div.className = "donemessage";
                    div.innerHTML = message;
                    document.body.insertBefore( div, document.body.firstChild );
                    }
                }

            original_email = $( '#email_input' ).val();
            original_username = $( '#name_input' ).val();

            $( '#login_info' ).bind( 'submit', function( e ) {
                var error_text_email= 'Please enter your valid email address.';
                var error_text_email_long= 'Email cannot be more than 255 characters in length.';
                var error_text_username_characters = 'Public name must contain only lowercase letters, numbers and "-". It also has to be shorter than 255 characters but longer than 3.';
                var email = $( '#email_input' ).val();
                var name = $( '#name_input' ).val();
                var validForm = true;
                var nothing_changed = ( original_email === email && original_username === name );
                // we need this value to detect submitting at backend
                var hidden_input = '<input type="hidden" id="login_info_button" name="login_info_button" value="Submit"/>';
                $( '#send' ).attr( 'disabled', 'disabled' );
                $( "#email_input" ).before( hidden_input );
                
                if ( original_email !== email ){
                    if ( email.length > 255 ){ renderError( error_text_email_long ); validForm = false; }
                    else if ( !validateString( email, "email" ) ){ renderError( error_text_email ); validForm = false; }
                }
                if ( original_username !== name ){
                    if ( name && !( validateString( name,"username" ) ) ){ renderError( error_text_username_characters ); validForm = false; }
                }
                if ( nothing_changed ){
                    renderDone( "Nothing has changed." );
                }
                if ( !validForm  || nothing_changed ) { 
                    e.preventDefault();
                    // reactivate the button if the form wasn't submitted
                    $( '#send' ).removeAttr( 'disabled' );
                    }
                });
        });

    </script>


    <h2>Manage User Information</h2>
    %if not is_admin:
        <ul class="manage-table-actions">
            <li>
                <a class="action-button"  href="${h.url_for( controller='user', action='index', cntrller=cntrller )}">User preferences</a>
            </li>
        </ul>
    %endif
    <div class="toolForm">
        <form name="login_info" id="login_info" action="${h.url_for( controller='user', action='edit_info', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
            <div class="toolFormTitle">Login Information</div>
            <div class="form-row">
                <label>Email address:</label>
                <input type="text" id ="email_input" name="email" value="${email}" size="40"/>
                <div class="toolParamHelp" style="clear: both;">
                    If you change your email address you will receive an activation link in the new mailbox and you have to activate your account by visiting it.
                </div>
            </div>
            <div class="form-row">
                <label>Public name:</label>
                %if t.webapp.name == 'tool_shed':
                    %if user.active_repositories:
                        <input type="hidden" name="username" value="${username}"/>
                        ${username}
                        <div class="toolParamHelp" style="clear: both;">
                            You cannot change your public name after you have created a repository in this tool shed.
                        </div>
                    %else:
                        <input type="text" name="username" size="40" value="${username}"/>
                        <div class="toolParamHelp" style="clear: both;">
                            Your public name provides a means of identifying you publicly within this tool shed. Public
                            names must be at least four characters in length and contain only lower-case letters, numbers,
                            and the '-' character.  You cannot change your public name after you have created a repository
                            in this tool shed.
                        </div>
                    %endif
                %else:
                    <input type="text" id="name_input" name="username" size="40" value="${username}"/>
                    <div class="toolParamHelp" style="clear: both;">
                        Your public name is an optional identifier that will be used to generate addresses for information
                        you share publicly. Public names must be at least four characters in length and contain only lower-case
                        letters, numbers, and the '-' character.
                    </div>
                %endif
            </div>
            <div class="form-row">
                <input type="submit" id="send" name="login_info_button" value="Save"/>
            </div>
        </form>
    </div>
    <p></p>
    <div class="toolForm">
        <form name="change_password" id="change_password" action="${h.url_for( controller='user', action='edit_info', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
            <div class="toolFormTitle">Change Password</div>
            %if not is_admin:
                <div class="form-row">
                    <label>Current password:</label>
                    <input type="password" name="current" value="" size="40"/>
                </div>
            %endif
            <div class="form-row">
                <label>New password:</label>
                <input type="password" name="password" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>Confirm:</label>
                <input type="password" name="confirm" value="" size="40"/>
            </div>
            <div class="form-row">
                <input type="submit" name="change_password_button" value="Save"/>
            </div>
        </form>
    </div>
</%def>
