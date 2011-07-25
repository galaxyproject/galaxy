<%inherit file="/base_panels.mako"/>

## Default title
<%def name="title()">Galaxy</%def>

## Masthead
<%def name="masthead()">

    ## Tab area, fills entire width
    <div style="position: relative; right: -50%; float: left; text-align: center;">
    
    <table class="tab-group" border="0" cellspacing="0" style="position: relative; right: 50%;">
    <tr>
    
    <%def name="tab( id, display, href, target='_parent', visible=True, extra_class='', menu_options=None )">
        ## Create a tab at the top of the panels. menu_options is a list of 2-elements lists of [name, link]
        ## that are options in the menu.
    
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
        <td class="${cls}" style="${style}">
            %if href:
                <a target="${target}" href="${href}">${display}</a>
            %else:
                <a>${display}</a>
            %endif
            %if menu_options:
                <div class="submenu">
                <ul>
                    %for menu_item in menu_options:
                        <li>
                        %if not menu_item:
                            <hr style="color: inherit; background-color: gray"/></li>
                        %else:
                            %if len ( menu_item ) == 1:
                                ${menu_item[0]}
                            %elif len ( menu_item ) == 2:
                                <% name, link = menu_item %>
                                <a href="${link}">${name}</a></li>
                            %else:
                                <% name, link, target = menu_item %>
                                <a target="${target}" href="${link}">${name}</a></li>
                            %endif
                        %endif
                    %endfor
                </ul>
                </div>
            %endif
        </td>
    </%def>
    

    ## Analyze data tab.
    ${tab( "analysis", "Analyze Data", h.url_for( controller='/root', action='index' ) )}
    
    ## Workflow tab.
    ${tab( "workflow", "Workflow", h.url_for( controller='/workflow', action='index' ) )}
    
    ## 'Shared Items' or Libraries tab.
    <%
        menu_options = [ 
                        [ 'Data Libraries', h.url_for( controller='/library', action='index') ],
                        None,
                        [ 'Published Histories', h.url_for( controller='/history', action='list_published' ) ],
                        [ 'Published Workflows', h.url_for( controller='/workflow', action='list_published' ) ]
                       ]
        if app.config.get_bool( 'enable_tracks', False ):
            menu_options.append( [ 'Published Visualizations', h.url_for( controller='/visualization', action='list_published' ) ] )        
        if app.config.get_bool( 'enable_pages', False ):
            menu_options.append( [ 'Published Pages', h.url_for( controller='/page', action='list_published' ) ] )
        tab( "shared", "Shared Data", h.url_for( controller='/library', action='index'), menu_options=menu_options )
    %>
    
    ## Lab menu.
    <%
        menu_options = [
                         [ 'Sequencing Requests', h.url_for( controller='/requests', action='index' ) ],
                         [ 'Find Samples', h.url_for( controller='/requests', action='find_samples_index' ) ],
                         [ 'Help', app.config.get( "lims_doc_url", "http://main.g2.bx.psu.edu/u/rkchak/p/sts" ), "galaxy_main" ]
                       ]
        tab( "lab", "Lab", None, menu_options=menu_options, visible=( trans.user and ( trans.user.requests or trans.app.security_agent.get_accessible_request_types( trans, trans.user ) ) ) )
    %>

    ## Visualization menu.
    %if app.config.get_bool( 'enable_tracks', False ):
        <%
            menu_options = [
                             ['New Track Browser', h.url_for( controller='/tracks', action='index' ) ],
                             ['Saved Visualizations', h.url_for( controller='/visualization', action='list' ) ]
                           ]
            tab( "visualization", "Visualization", h.url_for( controller='/visualization', action='list'), menu_options=menu_options )
        %>
    %endif

    ## Admin tab.
    ${tab( "admin", "Admin", h.url_for( controller='/admin', action='index' ), extra_class="admin-only", visible=( trans.user and app.config.is_admin_user( trans.user ) ) )}
    
    ## Help tab.
    <%
        menu_options = [
                            ['Email comments, bug reports, or suggestions', app.config.get( "bugs_email", "mailto:galaxy-bugs@bx.psu.edu"  ) ],
                            ['Galaxy Wiki', app.config.get( "wiki_url", "http://wiki.g2.bx.psu.edu/" ), "_blank" ],
                            ['Video tutorials (screencasts)', app.config.get( "screencasts_url", "http://galaxycast.org" ), "_blank" ],
                            ['How to Cite Galaxy', app.config.get( "screencasts_url", "http://wiki.g2.bx.psu.edu/Citing%20Galaxy" ), "_blank" ]
                        ]
        tab( "help", "Help", None, menu_options=menu_options)
    %>
    
    ## User tabs.
    <%  
        # Menu for user who is not logged in.
        menu_options = [ [ "Login", h.url_for( controller='/user', action='login' ), "galaxy_main" ] ]
        if app.config.allow_user_creation:
            menu_options.append( [ "Register", h.url_for( controller='/user', action='create', cntrller='user' ), "galaxy_main" ] ) 
        extra_class = "loggedout-only"
        visible = ( trans.user == None )
        tab( "user", "User", None, visible=visible, menu_options=menu_options )
        
        # Menu for user who is logged in.
        if trans.user:
            email = trans.user.email
        else:
            email = ""
        menu_options = [ [ '<li>Logged in as <span id="user-email">%s</span></li>' %  email ] ]
        if app.config.use_remote_user:
            if app.config.remote_user_logout_href:
                menu_options.append( [ 'Logout', app.config.remote_user_logout_href, "_top" ] )
        else:
            menu_options.append( [ 'Preferences', h.url_for( controller='/user', action='index', cntrller='user' ), "galaxy_main" ] )
            if app.config.get_bool( 'enable_tracks', False ):
                menu_options.append( [ 'Custom Builds', h.url_for( controller='/user', action='dbkeys' ), "galaxy_main" ] )
            if app.config.require_login:
                logout_url = h.url_for( controller='/root', action='index', m_c='user', m_a='logout' )
            else:
                logout_url = h.url_for( controller='/user', action='logout' )
            menu_options.append( [ 'Logout', logout_url, "_top" ] )
            menu_options.append( None )
        menu_options.append( [ 'Saved Histories', h.url_for( controller='/history', action='list' ), "galaxy_main" ] )
        menu_options.append( [ 'Saved Datasets', h.url_for( controller='/dataset', action='list' ), "galaxy_main" ] )
        if app.config.get_bool( 'enable_pages', False ):
            menu_options.append( [ 'Saved Pages', h.url_for( controller='/page', action='list' ), "_top" ] )
        if app.config.enable_api:
            menu_options.append( [ 'API Keys', h.url_for( controller='/user', action='api_keys', cntrller='user' ), "galaxy_main" ] )
        if app.config.use_remote_user:
            menu_options.append( [ 'Public Name', h.url_for( controller='/user', action='edit_username', cntrller='user' ), "galaxy_main" ] )
    
        extra_class = "loggedin-only"
        visible = ( trans.user != None )
        tab( "user", "User", None, visible=visible, menu_options=menu_options )
    %>
    
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
