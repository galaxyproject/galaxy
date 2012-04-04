<%inherit file="/base_panels.mako"/>

## Default title
<%def name="title()">Galaxy Tool Shed</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery.tipsy" )}
</%def>

## Masthead
<%def name="masthead()">

    ## Tab area, fills entire width
    <div style="position: relative; right: -50%; float: left;">
        <div style="display: block; position: relative; right: 50%;">

            <ul class="nav" border="0" cellspacing="0">
    
                <%def name="tab( id, display, href, target='_parent', visible=True, extra_class='', menu_options=None )">
                    <%
                    cls = ""
                    a_cls = ""
                    extra = ""
                    if extra_class:
                        cls += " " + extra_class
                    if self.active_view == id:
                        cls += " active"
                    if menu_options:
                        cls += " dropdown"
                        a_cls += " dropdown-toggle"
                        extra = "<b class='caret'></b>"
                    style = ""
                    if not visible:
                        style = "display: none;"
                    %>
                    <li class="${cls}" style="${style}">
                        %if href:
                            <a class="${a_cls}" data-toggle="dropdown" target="${target}" href="${href}">${display}${extra}</a>
                        %else:
                            <a class="${a_cls}" data-toggle="dropdown">${display}${extra}</a>
                        %endif
                        %if menu_options:
                            <ul class="dropdown-menu">
                                %for menu_item in menu_options:
                                    %if not menu_item:
                                        <li class="divider"></li>
                                    %else:
                                        <li>
                                        %if len ( menu_item ) == 1:
                                            ${menu_item[0]}
                                        %elif len ( menu_item ) == 2:
                                            <% name, link = menu_item %>
                                            <a href="${link}">${name}</a>
                                        %else:
                                            <% name, link, target = menu_item %>
                                            <a target="${target}" href="${link}">${name}</a>
                                        %endif
                                        </li>
                                    %endif
                                %endfor
                            </ul>
                        %endif
                    </li>
                </%def>

                ## Repositories tab.
                ${tab( "repositories", "Repositories", h.url_for( controller='/repository', action='index', webapp='community' ) )}
                
                ## Admin tab.
                ${tab( "admin", "Admin", h.url_for( controller='/admin', action='index', webapp='community' ), extra_class="admin-only", visible=( trans.user and app.config.is_admin_user( trans.user ) ) )}

                ## Help tab.
                <%
                    menu_options = [          
                        [_('Support'), app.config.get( "support_url", "http://wiki.g2.bx.psu.edu/Support" ), "_blank" ],
                        [_('Tool shed wiki'), app.config.get( "wiki_url", "http://wiki.g2.bx.psu.edu/Tool%20Shed" ), "_blank" ],
                        [_('Galaxy wiki'), app.config.get( "wiki_url", "http://wiki.g2.bx.psu.edu/" ), "_blank" ],
                        [_('Video tutorials (screencasts)'), app.config.get( "screencasts_url", "http://galaxycast.org" ), "_blank" ],
                        [_('How to Cite Galaxy'), app.config.get( "citation_url", "http://wiki.g2.bx.psu.edu/Citing%20Galaxy" ), "_blank" ]
                    ]
                    tab( "help", _("Help"), None, menu_options=menu_options)
                %>

                ## User tabs.
                <%  
                    # Menu for user who is not logged in.
                    menu_options = [ [ _("Login"), h.url_for( controller='/user', action='login', webapp='community' ), "galaxy_main" ] ]
                    if app.config.allow_user_creation:
                        menu_options.append( [ _("Register"), h.url_for( controller='/user', action='create', cntrller='user', webapp='community' ), "galaxy_main" ] ) 
                    extra_class = "loggedout-only"
                    visible = ( trans.user == None )
                    tab( "user", _("User"), None, visible=visible, menu_options=menu_options )
                    # Menu for user who is logged in.
                    if trans.user:
                        email = trans.user.email
                    else:
                        email = ""
                    menu_options = [ [ '<a>Logged in as <span id="user-email">%s</span></a>' %  email ] ]
                    if app.config.use_remote_user:
                        if app.config.remote_user_logout_href:
                            menu_options.append( [ _('Logout'), app.config.remote_user_logout_href, "_top" ] )
                    else:
                        menu_options.append( [ _('Preferences'), h.url_for( controller='/user', action='index', cntrller='user', webapp='community' ), "galaxy_main" ] )
                        logout_url = h.url_for( controller='/user', action='logout', webapp='community' )
                        menu_options.append( [ 'Logout', logout_url, "_top" ] )
                        menu_options.append( None )
                    if app.config.use_remote_user:
                        menu_options.append( [ _('Public Name'), h.url_for( controller='/user', action='edit_username', cntrller='user', webapp='community' ), "galaxy_main" ] )
            
                    extra_class = "loggedin-only"
                    visible = ( trans.user != None )
                    tab( "user", "User", None, visible=visible, menu_options=menu_options )
                %>
            </ul>
        </div>
    </div>
    
    ## Logo, layered over tabs to be clickable
    <div class="title">
        <a href="${app.config.get( 'logo_url', '/' )}">
        <img border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}">
        Galaxy Tool Shed
        %if app.config.brand:
            <span>/ ${app.config.brand}</span>
        %endif
        </a>
    </div>
</%def>
