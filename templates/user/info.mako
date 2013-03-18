<%inherit file="/base.mako"/>

<% is_admin = cntrller == 'admin' and trans.user_is_admin() %>

<%def name="render_user_info()">
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
                <input type="text" name="email" value="${email}" size="40"/>
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
                    <input type="text" name="username" size="40" value="${username}"/>
                    <div class="toolParamHelp" style="clear: both;">
                        Your public name is an optional identifier that will be used to generate addresses for information
                        you share publicly. Public names must be at least four characters in length and contain only lower-case
                        letters, numbers, and the '-' character.
                    </div>
                %endif
            </div>
            <div class="form-row">
                <input type="submit" name="login_info_button" value="Save"/>
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
