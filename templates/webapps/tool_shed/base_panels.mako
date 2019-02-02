<%inherit file="/base/base_panels.mako"/>

## Default title
<%def name="title()">Galaxy Tool Shed</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        $(document).ready( function() {

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
        <script>
          (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
          (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
          m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
          })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
          ga('create', '${app.config.ga_code}', 'auto');
          ga('send', 'pageview');
        </script>
    %endif

    ## start main tag
    <div id="masthead" class="navbar navbar-fixed-top navbar-inverse">

    ## Tab area, fills entire width
    <div style="position: relative; right: -50%; float: left;">
        <div style="display: block; position: relative; right: 50%;">

            <ul class="nav navbar-nav" border="0" cellspacing="0">
    
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
                            <a class="${a_cls}"  target="${target}" href="${href}">${display}${extra}</a>
                        %else:
                            <a class="${a_cls}" >${display}${extra}</a>
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
                                            <a href="${link}">${name | h}</a>
                                        %else:
                                            <% name, link, target = menu_item %>
                                            <a target="${target}" href="${link}">${name | h}</a>
                                        %endif
                                        </li>
                                    %endif
                                %endfor
                            </ul>
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
                    qa_url = app.config.get( "qa_url", None )
                    if qa_url:
                        menu_options = [ [_('Galaxy Q&A'), qa_url, "_blank" ] ]
                    menu_options.extend( [
                        [_('Tool Shed Wiki'), app.config.get( "wiki_url", "https://wiki.galaxyproject.org/ToolShed" ), "_blank" ],
                        [_('Support'), app.config.get( "support_url", "https://wiki.galaxyproject.org/Support" ), "_blank" ],
                        [_('Search'), app.config.get( "search_url", "http://galaxyproject.org/search/usegalaxy/" ), "_blank" ],
                        [_('Mailing Lists'), app.config.get( "mailing_lists_url", "https://wiki.galaxyproject.org/MailingLists" ), "_blank" ],
                        [_('Videos'), app.config.get( "screencasts_url", "https://vimeo.com/galaxyproject" ), "_blank" ],
                        [_('Wiki'), app.config.get( "wiki_url", "http://galaxyproject.org/" ), "_blank" ],
                        [_('How to Cite Galaxy'), app.config.get( "citation_url", "https://wiki.galaxyproject.org/CitingGalaxy" ), "_blank" ]
                    ] )
                    tab( "help", _("Help"), None, menu_options=menu_options )
                %>

                ## User tabs.
                <%
                    from markupsafe import escape 
                    # Menu for user who is not logged in.
                    menu_options = [ [ _("Login"), h.url_for( controller='/user', action='login' ), "galaxy_main" ] ]
                    if app.config.allow_user_creation:
                        menu_options.append( [ _("Register"), h.url_for( controller='/user', action='create', cntrller='user' ), "galaxy_main" ] ) 
                    extra_class = "loggedout-only"
                    visible = ( trans.user == None )
                    tab( "user", _("User"), None, visible=visible, menu_options=menu_options )
                    # Menu for user who is logged in.
                    if trans.user:
                        email = escape( trans.user.email )
                    else:
                        email = ""
                    menu_options = [ [ '<a>Logged in as <span id="user-email">%s</span></a>' %  email ] ]
                    if app.config.use_remote_user:
                        if app.config.remote_user_logout_href:
                            menu_options.append( [ _('Logout'), app.config.remote_user_logout_href, "_top" ] )
                    else:
                        menu_options.append( [ _('Preferences'), h.url_for( controller='/user', action='index', cntrller='user' ), "galaxy_main" ] )
                        menu_options.append( [ _('API Keys'), h.url_for( controller='/user', action='api_keys', cntrller='user' ), "galaxy_main" ] )
                        logout_url = h.url_for( controller='/user', action='logout' )
                        menu_options.append( [ 'Logout', logout_url, "_top" ] )
                        menu_options.append( None )
                    if app.config.use_remote_user:
                        menu_options.append( [ _('Public Name'), h.url_for( controller='/user', action='edit_username', cntrller='user' ), "galaxy_main" ] )
            
                    extra_class = "loggedin-only"
                    visible = ( trans.user != None )
                    tab( "user", "User", None, visible=visible, menu_options=menu_options )
                %>
            </ul>
        </div>
    </div>
    
    ## Logo, layered over tabs to be clickable
    <div class="navbar-brand">
        <a href="${h.url_for( app.config.get( 'logo_url', '/' ) )}">
        <img style="margin-left: 0.35em;" border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}">
        Galaxy Tool Shed
        %if app.config.brand:
            <span>/ ${app.config.brand}</span>
        %endif
        </a>
    </div>
    
    ## end main tag
    </div>
</%def>
