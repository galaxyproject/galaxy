<%!
    def inherit(context):
        if context.get('use_panels'):
            if context.get('webapp'):
                webapp = context.get('webapp')
            else:
                webapp = 'galaxy'
            return '/webapps/%s/base_panels.mako' % webapp
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
<%namespace file="login.mako" import="render_login_form" />
<%namespace file="register.mako" import="render_registration_form" />

<%def name="center_panel()">
    ${body()}
</%def>

<%def name="body()">

    <div style="overflow: auto; height: 100%">
    %if context.get('use_panels'):
        <div class="page-container" style="padding: 10px;">
    %else:
        <div class="page-container">
    %endif

    %if message:
        ${render_msg( message, status )}
    %endif

    <h2>OpenID Account Association</h2>
    <div>
        OpenIDs must be associated with a Galaxy account before they can be used for authentication.  This only needs to be done once per OpenID.  You may associate your OpenID with an existing Galaxy account, or create a new one.
    </div>
    <br/>

    %if len( openids ) > 1:
        <div>
            The following OpenIDs will be associated with the account chosen or created below.
            <ul>
            %for openid in openids:
                <li>${openid.openid}</li>
            %endfor
            </ul>
        </div>
    %else:
        <div>
            The OpenID <strong>${openids[0].openid}</strong> will be associated with the account chosen or created.
        </div>
    %endif
    <br/>

    <% form_action = h.url_for( cntrller=cntrller, use_panels=use_panels ) %>

    ${render_login_form( form_action=form_action )}

    <br/>

    ${render_registration_form( form_action=form_action )}

    </div>
    </div>

</%def>
