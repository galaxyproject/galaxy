<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Reset Password</div>
    <form name="reset_password" id="reset_password" action="${h.url_for( controller='user', action='reset_password' )}" method="post" >
        <div class="form-row">
            <label>Email:</label>
            <input type="text" name="email" value="" size="40"/>
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <input type="submit" name="reset_password_button" value="Submit"/>
        </div>
    </form>
</div>
