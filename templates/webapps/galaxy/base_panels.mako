<%inherit file="/base_panels.mako"/>

## Default title
<%def name="title()">Galaxy</%def>

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
    
    %if app.config.cloud_controller_instance:
        ${tab( "cloud", "Cloud", h.url_for( controller='/cloud', action='index' ))}
    %else:
        ${tab( "analysis", "Analyze Data", h.url_for( controller='/root', action='index' ))}
        
        ${tab( "workflow", "Workflow", h.url_for( controller='/workflow', action='index' ))}
        
        ${tab( "libraries", "Data Libraries", h.url_for( controller='/library', action='index' ))}
    %endif
    
    %if trans.user and trans.user.accessible_request_types(trans):
        <td class="tab">
            <a>Lab</a>
            <div class="submenu">
            <ul>            
                <li><a href="${h.url_for( controller='/requests', action='index' )}">Sequencing Requests</a></li>
                <li><a target="_blank" href="${app.config.get( "lims_doc_url", "http://main.g2.bx.psu.edu/u/rkchak/p/sts" )}">Help</a></li>
            </ul>
            </div>
        </td>
    %endif

    %if app.config.get_bool( 'enable_tracks', False ):
    <%
    cls = "tab"
    if self.active_view == 'visualization':
        cls += " active"
    %>
    <td class="${cls}">
        Visualization
        <div class="submenu">
        <ul>
            <li><a href="${h.url_for( controller='/tracks', action='index' )}">New Track Browser</a></li>
            <li><hr style="color: inherit; background-color: gray"/></li>
        <li><a href="${h.url_for( controller='/visualization', action='list' )}">Saved Visualizations</a></li>
        </ul>
        </div>
    </td>
    %endif

    ${tab( "admin", "Admin", h.url_for( controller='/admin', action='index' ), extra_class="admin-only", visible=( trans.user and app.config.is_admin_user( trans.user ) ) )}
    
    <td class="tab">
        <a>Help</a>
        <div class="submenu">
        <ul>            
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
            <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='login' )}">Login</a></li>
            %if app.config.allow_user_creation:
            <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='create' )}">Register</a></li>
            %endif
        </ul>
        <ul class="loggedin-only" style="${style2}">
            <li>Logged in as <span id="user-email">${user_email}</span></li>
            %if app.config.use_remote_user:
                %if app.config.remote_user_logout_href:
                    <li><a target="galaxy_main" href="${app.config.remote_user_logout_href}">Logout</a></li>
                %endif
            %else:
                <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='index' )}">Preferences</a></li>
                <%
                    if app.config.require_login:
                        logout_url = h.url_for( controller='/root', action='index', m_c='user', m_a='logout' )
                    else:
                        logout_url = h.url_for( controller='/user', action='logout' )
                %>
                %if app.config.get_bool( 'enable_tracks', False ):
                    <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='dbkeys' )}">Custom Builds</a></li>
                %endif
                <li><a target="_top" href="${logout_url}">Logout</a></li>
                <li><hr style="color: inherit; background-color: gray"/></li>
            %endif
            <li><a target="galaxy_main" href="${h.url_for( controller='/history', action='list' )}">Histories</a></li>
            <li><a target="galaxy_main" href="${h.url_for( controller='/dataset', action='list' )}">Datasets</a></li>
            %if app.config.get_bool( 'enable_pages', False ):
                <li><a href="${h.url_for( controller='/page', action='list' )}">Pages</a></li>  
            %endif
            %if app.config.enable_api:
                <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='api_keys' )}">API Keys</a></li>
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
        Galaxy
        %if app.config.brand:
            <span class='brand'>/ ${app.config.brand}</span>
        %endif
        </a>
    </div>
    
</%def>
