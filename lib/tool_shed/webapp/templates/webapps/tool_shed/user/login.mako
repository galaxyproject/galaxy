<%inherit file="/base.mako"/>

<%namespace file="/message.mako" import="render_msg" />

<%def name="body()">
    <%
        form_action = h.url_for( controller='user', action='login', use_panels=use_panels )
    %>
    %if header:
        ${header}
    %endif
    <div class="toolForm">
        <div class="toolFormTitle">Login</div>
        <form name="login" id="login" action="${form_action}" method="post" >
            <input type="hidden" name="session_csrf_token" value="${trans.session_csrf_token}" />
            <div class="form-row">
                <label>Username / Email Address:</label>
                <input type="text" name="login" value="${login or ''| h}" size="40"/>
                <input type="hidden" name="redirect" value="${redirect | h}" size="40"/>
            </div>
            <div class="form-row">
                <label>Password:</label>
                <input type="password" name="password" value="" size="40"/>
                <div class="toolParamHelp" style="clear: both;">
                    <a href="${h.url_for( controller='user', action='reset_password', use_panels=use_panels )}">Forgot password? Reset here</a>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="login_button" value="Login"/>
            </div>
        </form>
    </div>
</%def>
