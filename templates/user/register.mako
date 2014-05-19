<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if redirect_url:
    <script type="text/javascript">  
        top.location.href = '${redirect_url | h}';
    </script>
%endif

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if not redirect_url and message:
    ${render_msg( message, status )}
%endif

## An admin user may be creating a new user account, in which case we want to display the registration form.
## But if the current user is not an admin user, then don't display the registration form.
%if trans.user_is_admin() or not trans.user:
    ${render_registration_form()}

    %if trans.app.config.get( 'terms_url', None ) is not None:
        <br/>
        <p>
            <a href="${trans.app.config.get('terms_url', None)}">Terms and Conditions for use of this service</a>
        </p>
    %endif
%endif

<%def name="render_registration_form( form_action=None )">

    <%
        if form_action is None:
            form_action = h.url_for( controller='user', action='create', cntrller=cntrller )
        from galaxy.web.form_builder import CheckboxField
        subscribe_check_box = CheckboxField( 'subscribe' )
    %>

<script type="text/javascript">
	$(document).ready(function() {

		function validateString(test_string, type) { 
			var mail_re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
			//var mail_re_RFC822 = /^([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x22([^\x0d\x22\x5c\x80-\xff]|\x5c[\x00-\x7f])*\x22))*\x40([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d)(\x2e([^\x00-\x20\x22\x28\x29\x2c\x2e\x3a-\x3c\x3e\x40\x5b-\x5d\x7f-\xff]+|\x5b([^\x0d\x5b-\x5d\x80-\xff]|\x5c[\x00-\x7f])*\x5d))*$/;
			var username_re = /^[a-z0-9\-]{3,255}$/;
			if (type === 'email') {
				return mail_re.test(test_string);
			} else if (type === 'username'){
				return username_re.test(test_string);
			}
		} 

		function renderError(message) {
		if ($(".errormessage").length === 1) {
			$(".errormessage").html(message)
		} else {
			var div = document.createElement("div");
			div.className = "errormessage";
			div.innerHTML = message;
			document.body.insertBefore(div, document.body.firstChild);
			}
		}

		$('#registration').bind('submit', function(e) {
			$('#send').attr('disabled', 'disabled');
            
            // we need this value to detect submitting at backend
			var hidden_input = '<input type="hidden" id="create_user_button" name="create_user_button" value="Submit"/>';
			$("#email_input").before(hidden_input);

			var error_text_email= 'Please enter your valid email address';
			var error_text_email_long= 'Email cannot be more than 255 characters in length';
			var error_text_username_characters = 'Public name must contain only lowercase letters, numbers and "-". It also has to be shorter than 255 characters but longer than 3.';
			var error_text_password_short = 'Please use a password of at least 6 characters';
			var error_text_password_match = "Passwords don't match";

		    var validForm = true;
		    
		    var email = $('#email_input').val();
		    var name = $('#name_input').val();
		    if (email.length > 255){ renderError(error_text_email_long); validForm = false;}
		    else if (!validateString(email,"email")){ renderError(error_text_email); validForm = false;}
		    else if (!($('#password_input').val() === $('#password_check_input').val())){ renderError(error_text_password_match); validForm = false;}
		    else if ($('#password_input').val().length < 6 ){ renderError(error_text_password_short); validForm = false;}
		    else if (name && !(validateString(name,"username"))){ renderError(error_text_username_characters); validForm = false;}

	   		if (!validForm) { 
		        e.preventDefault();
		        // reactivate the button if the form wasn't submitted
		        $('#send').removeAttr('disabled');
		        }
			});
	});

</script>
    <div class="toolForm">
        <form name="registration" id="registration" action="${form_action}" method="post" >
            <div class="toolFormTitle">Create account</div>
            <div class="form-row">
                <label>Email address:</label>
                <input id="email_input" type="text" name="email" value="${email | h}" size="40"/>
                <input type="hidden" name="redirect" value="${redirect | h}" size="40"/>
            </div>
            <div class="form-row">
                <label>Password:</label>
                <input id="password_input" type="password" name="password" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>Confirm password:</label>
                <input id="password_check_input" type="password" name="confirm" value="" size="40"/>
            </div>
            <div class="form-row">
                <label>Public name:</label>
                <input id="name_input" type="text" name="username" size="40" value="${username |h}"/>
                %if t.webapp.name == 'galaxy':
                    <div class="toolParamHelp" style="clear: both;">
                        Your public name is an identifier that will be used to generate addresses for information
                        you share publicly. Public names must be at least four characters in length and contain only lower-case
                        letters, numbers, and the '-' character.
                    </div>
                %else:
                    <div class="toolParamHelp" style="clear: both;">
                        Your public name provides a means of identifying you publicly within this tool shed. Public
                        names must be at least four characters in length and contain only lower-case letters, numbers,
                        and the '-' character.  You cannot change your public name after you have created a repository
                        in this tool shed.
                    </div>
                %endif
            </div>
            %if trans.app.config.smtp_server:
                <div class="form-row">
                    <label>Subscribe to mailing list:</label>
                    %if subscribe_checked:
                        <% subscribe_check_box.checked = True %>
                    %endif
                    ${subscribe_check_box.get_html()}
                    <p>See <a href="http://galaxyproject.org/wiki/Mailing%20Lists" target="_blank">
                    all Galaxy project mailing lists</a>.</p>
                </div>
            %endif
            %if user_type_fd_id_select_field and len( user_type_fd_id_select_field.options ) >= 1:
                <div class="form-row">
                    <label>User type</label>
                    ${user_type_fd_id_select_field.get_html()}
                </div>
            %endif
            %if user_type_form_definition:
                %for field in widgets:
                    <div class="form-row">
                        <label>${field['label']}</label>
                        ${field['widget'].get_html()}
                        <div class="toolParamHelp" style="clear: both;">
                            ${field['helptext']}
                        </div>
                        <div style="clear: both"></div>
                    </div>
                %endfor
                %if not user_type_fd_id_select_field:
                    <input type="hidden" name="user_type_fd_id" value="${trans.security.encode_id( user_type_form_definition.id )}"/>
                %endif   
            %endif
            <div id="for_bears">
            If you see this, please leave following field blank. 
            <input type="text" name="bear_field" size="1" value=""/>
            </div>
            <div class="form-row">
                <input type="submit" id="send" name="create_user_button" value="Submit"/>
            </div>
        </form>
        %if registration_warning_message:
        <div class="alert alert-danger" style="margin: 30px 12px 12px 12px;">
            ${registration_warning_message}           
        </div>
        %endif
    </div>

</%def>
