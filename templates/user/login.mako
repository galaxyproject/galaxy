<%!
#This is a hack, we should restructure templates to avoid this.
def inherit(context):
    if context.get('trans').webapp.name == 'galaxy' and context.get( 'use_panels', True ):
        return '/webapps/galaxy/base_panels.mako'
    elif context.get('trans').webapp.name == 'tool_shed' and context.get( 'use_panels', True ):
        return '/webapps/tool_shed/base_panels.mako'
    else:
        return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view=active_view
    self.message_box_visible=False
%>
</%def>

<%namespace file="/message.mako" import="render_msg" />

<%def name="center_panel()">
    ${body()}
</%def>

<%def name="body()">

    %if redirect_url:
        <script type="text/javascript">  
            top.location.href = '${redirect_url | h}';
        </script>
    %endif

    %if context.get('use_panels'):
        <div style="margin: 1em;">
    %else:
        <div>
    %endif

    %if message:
        ${render_msg( message, status )}
    %endif

    %if not trans.user:

        ${render_login_form()}

        %if trans.app.config.enable_openid:
            <br/>
            ${render_openid_form( redirect, False, openid_providers )}
        %endif

        %if trans.app.config.get( 'terms_url', None ) is not None:
            <br/>
            <p>
                <a href="${trans.app.config.get('terms_url', None)}">Terms and Conditions for use of this service</a>
            </p>
        %endif

    %endif

    </div>

</%def>

<%def name="render_login_form( form_action=None )">

    <%
        if form_action is None:
            form_action = h.url_for( controller='user', action='login', use_panels=use_panels )
    %>

    %if header:
        ${header}
    %endif
    <div class="toolForm">
        <div class="toolFormTitle">Login</div>
        <form name="login" id="login" action="${form_action}" method="post" >
            <div class="form-row">
                <label>Email address:</label>
                <input type="text" name="email" value="${email | h}" size="40"/>
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

<%def name="render_openid_form( redirect, auto_associate, openid_providers )">
    <div class="toolForm">
        <div class="toolFormTitle">OpenID Login</div>
        <form name="openid" id="openid" action="${h.url_for( controller='user', action='openid_auth' )}" method="post" target="_parent" >
            <div class="form-row">
                <label>OpenID URL:</label>
                <input type="text" name="openid_url" size="60" style="background-image:url('${h.url_for( '/static/images/openid-16x16.gif' )}' ); background-repeat: no-repeat; padding-right: 20px; background-position: 99% 50%;"/>
                <input type="hidden" name="redirect" value="${redirect | h}" size="40"/>
            </div>
            <div class="form-row">
                Or, authenticate with your <select name="openid_provider">
                %for provider in openid_providers:
                    <option value="${provider.id}">${provider.name}</option>
                %endfor
                </select> account.
            </div>
            <div class="form-row">
                <input type="submit" name="login_button" value="Login"/>
            </div>
        </form>
    </div>

</%def>
