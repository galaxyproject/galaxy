<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <form name="change_password" id="change_password" action="${h.url_for( controller='user', action='change_password' )}" method="post" >
        <div class="toolFormTitle">Change Password</div>
        %if token:
            <input type="hidden" name="token" value="${token|h}"/>
        %elif not is_admin:
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
