<%inherit file="/base.mako"/>
<%def name="body()">
    <h2>Associate more OpenIDs</h2>
    ${render_openid_form( redirect, True, openid_providers )}
</%def>

<%def name="render_openid_form( redirect, auto_associate, openid_providers )">
    <div class="toolForm">
        <div class="toolFormTitle">OpenID Login</div>
        <form name="openid" id="openid" action="${h.url_for( controller='user', action='login' )}" method="post" target="_parent" >
            <div class="form-row">
                <label>OpenID URL:</label>
                <input type="hidden" name="method" value="redirect"/>
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
