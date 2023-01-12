<%inherit file="/base/base_panels.mako"/>
<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />

## Default title
<%def name="title()">Tool Shed</%def>

<%def name="init()">
    ${parent.init()}
    <%
        self.body_class = "toolshed"
    %>
</%def>

<%def name="javascript_app()">
    ${parent.javascript_app()}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("toolshed/base_panels.mako", "hardcoded dropdown init");

            // Masthead dropdown menus
            var $dropdowns = $("#masthead ul.nav > li.dropdown > .dropdown-menu");
            $("body").on( "click.nav_popups", function( e ) {
                $dropdowns.hide();
                $("#dd-helper").hide();
                // If the target is in the menu, treat normally
                if ( $(e.target).closest( "#masthead ul.nav > li.dropdown > .dropdown-menu" ).length ) {
                    return;
                }
                // Otherwise, was the click in a tab
                var $clicked = $(e.target).closest( "#masthead ul.nav > li.dropdown" );
                if ( $clicked.length ) {
                    $("#dd-helper").show();
                    $clicked.children( ".dropdown-menu" ).show();
                    e.preventDefault();
                }
            });
        });
    </script>
</%def>

## Masthead
<%def name="masthead()">

    %if app.config.ga_code:
        ${ galaxy_client.config_google_analytics(app.config.ga_code)}
    %endif
    %if app.config.plausible_server and app.config.plausible_domain:
        ${ galaxy_client.config_plausible_analytics(app.config.plausible_server, app.config.plausible_domain) }
    %endif
    %if app.config.matomo_server:
        ${ galaxy_client.config_matomo_analytics(app.config.matomo_server) }
    %endif

    ## start main tag
    <nav id="masthead" class="masthead-toolshed navbar navbar-expand navbar-fixed-top justify-content-center navbar-dark">

        ## Logo, layered over tabs to be clickable
        <a href="${h.url_for( app.config.get( 'logo_url', '/' ) )}" aria-label="homepage" class="navbar-brand">
            <img alt="logo" class="navbar-brand-image" src="${h.url_for('/static/favicon.svg')}">
            <span class="navbar-brand-title">
                Tool Shed
                %if app.config.brand:
                    / ${app.config.brand}
                %endif
            </span>
        </a>

        ## Tab area, fills entire width
        <ul class="navbar-nav">
            <%def name="tab( id, display, href, target='_parent', visible=True, extra_class='', menu_options=None )">
                <%
                cls = "nav-item"
                a_cls = "nav-link"
                extra = ""
                if extra_class:
                    cls = extra_class
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
                    <a
                    %if href:
                        class="${a_cls}" target="${target}" href="${href}"
                    %else:
                        class="${a_cls}"
                    %endif
                    %if menu_options:
                        role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"
                    %endif
                    >
                        ${display}${extra}
                    </a>
                    %if menu_options:
                        <div class="dropdown-menu" aria-labelledby="navbarDropdown">
                            %for menu_item in menu_options:
                                %if not menu_item:
                                    <div class="dropdown-divider"></div>
                                %else:
                                    %if len ( menu_item ) == 1:
                                        <a class="dropdown-item" href="javascript:void(0)" role="button">
                                            ${menu_item[0]}
                                        </a>
                                    %elif len ( menu_item ) == 2:
                                        <% name, link = menu_item %>
                                        <a class="dropdown-item" href="${link}">${name | h}</a>
                                    %else:
                                        <% name, link, target = menu_item %>
                                        <a class="dropdown-item" target="${target}" href="${link}">${name | h}</a>
                                    %endif
                                %endif
                            %endfor
                        </div>
                    %endif
                </li>
            </%def>

            ## Repositories tab.
            ${tab( "repositories", "Repositories", h.url_for( controller='/repository', action='index' ) )}

            ## Groups tab.
            ${tab( "groups", "Groups", h.url_for( controller='/groups', action='index' ) )}

            ## Admin tab.
            ${tab( "admin", "Admin", h.url_for( controller='/admin', action='index' ), extra_class="admin-only", visible=( trans.user and app.config.is_admin_user( trans.user ) ) )}

            ## Help tab.
            <%
                menu_options = []
                menu_options.extend( [
                    ['About Tool Shed', app.config.get( "wiki_url", "https://galaxyproject.org/toolshed" ), "_blank" ],
                    ['Support', app.config.get( "support_url", "https://galaxyproject.org/support" ), "_blank" ],
                    ['Videos', app.config.get( "screencasts_url", "https://vimeo.com/galaxyproject" ), "_blank" ],
                    ['How to Cite Tool Shed', app.config.get( "citation_url", "https://galaxyproject.org/citing-galaxy" ), "_blank" ]
                ] )
                tab( "help", "Help", None, menu_options=menu_options )
            %>

            ## User tabs.
            <%
                from markupsafe import escape
                # Menu for user who is not logged in.
                menu_options = [ [ "Login", h.url_for( controller='/user', action='login' ), "galaxy_main" ] ]
                if app.config.allow_user_creation:
                    menu_options.append( [ "Register", h.url_for( controller='/user', action='create', cntrller='user' ), "galaxy_main" ] )
                extra_class = "loggedout-only"
                visible = ( trans.user == None )
                tab( "user", "User", None, visible=visible, menu_options=menu_options )
                # Menu for user who is logged in.
                if trans.user:
                    email = escape( trans.user.email )
                else:
                    email = ""
                menu_options = [ [ 'Logged in as <span id="user-email">%s</span>' %  email ] ]
                if app.config.use_remote_user:
                    if app.config.remote_user_logout_href:
                        menu_options.append( [ 'Logout', app.config.remote_user_logout_href, "_top" ] )
                else:
                    menu_options.append( [ 'Preferences', h.url_for( controller='/user', action='index', cntrller='user' ), "galaxy_main" ] )
                    menu_options.append( [ 'API Keys', h.url_for( controller='/user', action='api_keys', cntrller='user' ), "galaxy_main" ] )
                    logout_url = h.url_for( controller='/user', action='logout' )
                    menu_options.append( [ 'Logout', logout_url, "_top" ] )
                if app.config.use_remote_user:
                    menu_options.append( [ 'Public Name', h.url_for( controller='/user', action='edit_username', cntrller='user' ), "galaxy_main" ] )

                extra_class = "loggedin-only"
                visible = ( trans.user != None )
                tab( "user", "User", None, visible=visible, menu_options=menu_options )
            %>
        </ul>
    </nav>
</%def>
