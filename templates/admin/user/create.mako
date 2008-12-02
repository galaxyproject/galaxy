<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create account</div>
    <div class="toolFormBody">
        <form name="form" action="${h.url_for( controller='admin', action='create_new_user' )}" method="post" >
            <div class="form-row">
                <label>Email address:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="email" value="${email}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
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
            <div class="form-row">
                <label>Subscribe To Mailing List:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="checkbox" name="subscribe" value="${subscribe}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="user_create_button" value="Create">
        </form>
    </div>
</div>
