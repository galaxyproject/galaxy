<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif
<div class="toolForm">
    <div class="toolFormTitle">Login</div>
    %if header:
        ${header}
    %endif
    <form name="login" id="login" action="${h.url_for( controller='user', action='login' )}" method="post" >
        <div class="form-row">
            <label>Email address:</label>
            <input type="text" name="email" value="" size="40"/>
            <input type="hidden" name="webapp" value="${webapp}" size="40"/>
            <input type="hidden" name="referer" value="${trans.request.referer}" size="40"/>
        </div>
        <div class="form-row">
            <label>Password:</label>
            <input type="password" name="password" value="" size="40"/>
            <div class="toolParamHelp" style="clear: both;">
                <a href="${h.url_for( controller='user', action='reset_password', webapp=webapp, use_panels=use_panels )}">Forgot password? Reset here</a>
            </div>
        </div>
        <div class="form-row">
            <input type="submit" name="login_button" value="Login"/>
        </div>
    </form>
</div>
