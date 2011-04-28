<%inherit file="/base.mako"/>

<% is_admin = cntrller == 'admin' and trans.user_is_admin() %>

<h2>Manage Public Name</h2>
<div class="toolForm">
    <form name="username" id="username" action="${h.url_for( controller='user', action='edit_username', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
        <input type="hidden" name="webapp" value="${webapp}" size="40"/>
        <div class="toolFormTitle">Login Information</div>
        <div class="form-row">
            <label>Public name:</label>
            <input type="text" name="username" size="40" value="${username}"/>
            <div class="toolParamHelp" style="clear: both;">
                Your public name is an optional identifier that will be used to generate addresses for information
                you share publicly. Public names must be at least four characters in length and contain only lower-case
                letters, numbers, and the '-' character.
            </div>
        </div>
        <div class="form-row">
            <input type="submit" name="change_username_button" value="Save"/>
        </div>
    </form>
</div>
