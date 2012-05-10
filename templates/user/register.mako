<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if redirect_url:
    <script type="text/javascript">  
        top.location.href = '${redirect_url}';
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
%endif

<%def name="render_registration_form( form_action=None )">

    <%
        if form_action is None:
            form_action = h.url_for( controller='user', action='create', cntrller=cntrller )
        from galaxy.web.form_builder import CheckboxField
        subscribe_check_box = CheckboxField( 'subscribe' )
    %>

    <div class="toolForm">
        <form name="registration" id="registration" action="${form_action}" method="post" >
            <div class="toolFormTitle">Create account</div>
            <div class="form-row">
                <label>Email address:</label>
                <input type="text" name="email" value="${email}" size="40"/>
                <input type="hidden" name="webapp" value="${webapp}" size="40"/>
                <input type="hidden" name="redirect" value="${redirect}" size="40"/>
            </div>
            <div class="form-row">
                <label>Password:</label>
                <input type="password" name="password" value="${password}" size="40"/>
            </div>
            <div class="form-row">
                <label>Confirm password:</label>
                <input type="password" name="confirm" value="${confirm}" size="40"/>
            </div>
            <div class="form-row">
                <label>Public name:</label>
                <input type="text" name="username" size="40" value="${username}"/>
                %if webapp == 'galaxy':
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
            %if user_type_fd_id_select_field and len( user_type_fd_id_select_field.options ) > 1:
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
            <div class="form-row">
                <input type="submit" name="create_user_button" value="Submit"/>
            </div>
        </form>
    </div>

</%def>
