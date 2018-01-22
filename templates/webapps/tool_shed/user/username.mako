<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<% is_admin = cntrller == 'admin' and trans.user_is_admin() %>

<h2>Manage Public Name</h2>
<div class="toolForm">
    <form name="username" id="username" action="${h.url_for( controller='user', action='edit_username', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
        <div class="toolFormTitle">Login Information</div>
        <div class="form-row">
            <label>Public name:</label>
            <input type="text" name="username" size="40" value="${username}"/>
            <div class="toolParamHelp" style="clear: both;">
                Your public name is an identifier that will be used to generate addresses for information
                you share publicly. Public names must be at least four characters in length and contain only lower-case
                letters, numbers, dots, underscores, and dashes ('.', '_', '-').
            </div>
        </div>
        <div class="form-row">
            <input type="submit" name="change_username_button" value="Save"/>
        </div>
    </form>
</div>
