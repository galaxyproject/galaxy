<%inherit file="/base_panels.mako"/>

## Default title
<%def name="title()">Galaxy Tool Shed</%def>

## Masthead
<%def name="masthead()">

    ## Tab area, fills entire width
    <div style="position: absolute; top: 0; left: 0; width: 100%; text-align: center">
    
    <table class="tab-group" border="0" cellspacing="0" style="margin: auto;">
    <tr>
    
    <%def name="tab( id, display, href, target='_parent', visible=True, extra_class='' )">
        <%
        cls = "tab"
        if extra_class:
            cls += " " + extra_class
        if self.active_view == id:
            cls += " active"
        style = ""
        if not visible:
            style = "display: none;"
        %>
        <td class="${cls}" style="${style}"><a target="${target}" href="${href}">${display}</a></td>
    </%def>

    %if trans.app.config.enable_next_gen_tool_shed:
        ${tab( "repositories", "Repositories", h.url_for( controller='/repository', action='index', webapp='community' ) )}
    %else:
        ${tab( "tools", "Tools", h.url_for( controller='/tool', action='index', webapp='community' ) )}
    %endif
    ${tab( "admin", "Admin", h.url_for( controller='/admin', action='index', webapp='community' ), extra_class="admin-only", visible=( trans.user and app.config.is_admin_user( trans.user ) ) )}
    
    <td class="tab">
        <a>Help</a>
        <div class="submenu">
        <ul>            
            <li><a target="galaxy_main" href="${h.url_for( controller='tool', action='help' )}">How to upload, download and install tools</a></li>
            <li><a href="${app.config.get( "bugs_email", "mailto:galaxy-bugs@bx.psu.edu"  )}">Email comments, bug reports, or suggestions</a></li>
            <li><a target="_blank" href="${app.config.get( "wiki_url", "http://bitbucket.org/galaxy/galaxy-central/wiki" )}">Galaxy Wiki</a></li>             
            <li><a target="_blank" href="${app.config.get( "screencasts_url", "http://galaxycast.org" )}">Video tutorials (screencasts)</a></li>
            <li><a target="_blank" href="${app.config.get( "citation_url", "http://bitbucket.org/galaxy/galaxy-central/wiki/Citations" )}">How to Cite Galaxy</a></li>
        </ul>
        </div>
    </td>
    
    ## User tab.
    <%
        cls = "tab"
        if self.active_view == 'user':
            cls += " active"
    %>
    <td class="${cls}">
        <a>User</a>
        <%
        if trans.user:
            user_email = trans.user.email
            style1 = "display: none;"
            style2 = "";
        else:
            user_email = ""
            style1 = ""
            style2 = "display: none;"
        %>
        <div class="submenu">
        <ul class="loggedout-only" style="${style1}">
            <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='login', webapp='community' )}">Login</a></li>
            %if app.config.allow_user_creation:
            <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='create', cntrller='user', webapp='community' )}">Register</a></li>
            %endif
        </ul>
        <ul class="loggedin-only" style="${style2}">
            %if app.config.use_remote_user:
                %if app.config.remote_user_logout_href:
                    <li><a href="${app.config.remote_user_logout_href}" target="_top">Logout</a></li>
                %endif
            %else:
                <li>Logged in as <span id="user-email">${user_email}</span></li>
                <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='index', cntrller='user', webapp='community' )}">Preferences</a></li>
                <%
                    if app.config.require_login:
                        logout_url = h.url_for( controller='/root', action='index', webapp='community', m_c='user', m_a='logout' )
                    else:
                        logout_url = h.url_for( controller='/user', action='logout', webapp='community' )
                %>
                <li><a target="_top" href="${logout_url}">Logout</a></li>
            %endif
        </ul>
        </div>
    </td>
    </tr>
    </table>
    </div>
    
    ## Logo, layered over tabs to be clickable
    <div class="title" style="position: absolute; top: 0; left: 0;">
        <a href="${app.config.get( 'logo_url', '/' )}">
        <img border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}" style="width: 26px; vertical-align: top;">
        Galaxy Tool Shed
        %if app.config.brand:
            <span class='brand'>/ ${app.config.brand}</span>
        %endif
        </a>
    </div>
    
</%def>
