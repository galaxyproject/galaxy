<%inherit file="/base.mako"/>

<%def name="render_user_info()">
    <h2>Manage User Information</h2>
    %if not admin_view:
        <ul class="manage-table-actions">
            <li>
                <a class="action-button"  href="${h.url_for( controller='user', action='index' )}">
                <span>User preferences</span></a>
            </li>
        </ul>
    %endif
    <div class="toolForm">
        <form name="login_info" id="login_info" action="${h.url_for( controller='user', action='edit_info', user_id=user.id, admin_view=admin_view )}" method="post" >
            <div class="toolFormTitle">Login Information</div>
            <div class="form-row">
                <label>Email address:</label>
                <input type="text" name="email" value="${email}" size="40"/>
            </div>
            <div class="form-row">
                <label>Public user name:</label>
                <input type="text" name="username" size="40" value="${username}"/>
                <div class="toolParamHelp" style="clear: both;">
                    Your user name is an optional identifier that will be used to generate addresses for information
                    you share publicly. User names must be at least four characters in length and contain only lower-case
                    letters, numbers, and the '-' character.
                </div>
            </div>
            <div class="form-row">
                <input type="hidden" name="webapp" value="${webapp}" size="40"/>
                <input type="submit" name="login_info_button" value="Save"/>
            </div>
        </form>
    </div>
    <p></p>
    <div class="toolForm">
        <form name="change_password" id="change_password" action="${h.url_for( controller='user', action='edit_info', user_id=user.id, admin_view=admin_view )}" method="post" >
            <div class="toolFormTitle">Change Password</div>
            %if not admin_view:
                <div class="form-row">
                    <label>Current Password:</label>
                    <input type="password" name="current" value="${current}" size="40"/>
                </div>
            %endif
            <div class="form-row">
                <label>New Password:</label>
                <input type="password" name="password" value="${password}" size="40"/>
            </div>
            <div class="form-row">
                <label>Confirm:</label>
                <input type="password" name="confirm" value="${confirm}" size="40"/>
            </div>
            <div class="form-row">
                <input type="hidden" name="webapp" value="${webapp}" size="40"/>
                <input type="submit" name="change_password_button" value="Save"/>
            </div>
        </form>
    </div>
</%def>
