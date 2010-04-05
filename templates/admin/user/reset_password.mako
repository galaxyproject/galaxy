<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Reset password for users</div>
    <div class="toolFormBody">
        <form name="form" action="${h.url_for( controller='admin', action='reset_user_password' )}" method="post" >
            <input type="hidden" name="id" value="${id}" size="40">
            %for user in users:
                <div class="form-row">
                    <label>Email:</label>
                    ${user.email}
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div class="form-row">
                <label>Password:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="password" name="password" value="${password}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Confirm password:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="password" name="confirm" value="${confirm}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="reset_user_password_button" value="Reset">
        </form>
    </div>
</div>
