## This needs to be on the first line, otherwise IE6 goes into quirks mode
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<%
    self.has_left_panel=True
    self.has_right_panel=True
    self.message_box_visible=False
    self.message_box_class=""
    self.active_view=None
%>
    
<%def name="init()">
    ## Override
</%def>

## Default title
<%def name="title()">Galaxy</%def>

## Default stylesheets
<%def name="stylesheets()">
    <link rel="stylesheet" type="text/css" href="${h.url_for('/static/style/reset.css')}" />
    <link rel="stylesheet" type="text/css" href="${h.url_for('/static/style/panel_layout.css')}" />
    <style type="text/css">
    #center {
        %if not self.has_left_panel:
            left: 0;
        %endif
        %if not self.has_right_panel:
            right: 0;
        %endif
    }
    %if self.message_box_visible:
        #left, #left-border, #center, #right-border, #right
        {
            top: 64px;
        }
    %endif
    </style>
</%def>

## Default javascripts
<%def name="javascripts()">
    <!--[if lt IE 7]>
    <script type='text/javascript' src="/static/scripts/IE7.js"> </script>
    <script type='text/javascript' src="/static/scripts/ie7-recalc.js"> </script>
    <![endif]-->
</%def>

## Default late-load javascripts
<%def name="late_javascripts()">
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    <script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>
    <script type="text/javascript" src="${h.url_for('/static/scripts/jquery.hoverIntent.js')}"></script>
    <script type="text/javascript" src="${h.url_for('/static/scripts/jquery.ui.js')}"></script>
    <script type="text/javascript" src="${h.url_for('/static/scripts/galaxy.panels.js')}"></script>
    <script type="text/javascript">
        
	ensure_dd_helper();
        
	%if self.has_left_panel:
            var lp = make_left_panel( $("#left"), $("#center"), $("#left-border" ) );
            force_left_panel = lp.force_panel;
        %endif
        
	%if self.has_right_panel:
            var rp = make_right_panel( $("#right"), $("#center"), $("#right-border" ) );
            handle_minwidth_hint = rp.handle_minwidth_hint;
            force_right_panel = rp.force_panel;
        %endif
	
	$(function() {
	    $("span.tab").each( function() {
		var submenu = $(this).children( "div.submenu" );
		if ( submenu.length > 0 ) {
		    if ( $.browser.msie ) {
			## Vile IE iframe hack -- even IE7 needs this
			submenu.prepend( "<iframe style=\"position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; filter:Alpha(Opacity='0');\"></iframe>" );
		    }
		    $(this).hoverIntent( function() { submenu.show(); }, function() { submenu.hide(); } );
		    submenu.click( function() { submenu.hide(); } );
		}
	    });
	});
	
	function user_changed( user_email, is_admin ) {
	    if ( user_email ) {
		$(".loggedin-only").show();
		$(".loggedout-only").hide();
		$("#user-email").text( user_email )
		if ( is_admin ) {
		    $(".admin-only").show();
		}
	    } else {
		$(".loggedin-only").hide();
		$(".loggedout-only").show();
		$(".admin-only").hide();
	    }
	}
	
    </script>
</%def>

## Masthead
<%def name="masthead()">

    <div class="title" style="float: left;">
	    <a target="_blank" href="${app.config.wiki_url}">
		<img border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}" style="width: 26px; vertical-align: top;">
	    </a>   
	    Galaxy
	    %if app.config.brand:
		<span class='brand'>/${app.config.brand}</span>
	    %endif
    </div>
    
    <div style="position: absolute; left: 50%;">
    <div class="tab-group" style="position: relative; left: -50%;">
	
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
	    <span class="${cls}" style="${style}"><a target="${target}" href="${href}">${display}</a></span>
	</%def>
    
	${tab( "analysis", "Analyze Data", h.url_for( controller='root', action='index' ))}

	${tab( "workflow", "Workflow", h.url_for( controller='workflow', action='index' ))}

	${tab( "admin", "Admin", h.url_for( controller='admin', action='index' ), extra_class="admin-only", visible=( trans.user and app.config.is_admin_user( trans.user ) ) )}
	
	<span class="tab">
	    <a>Help</a>
	    <div class="submenu">
		<ul>		    
		    <li><a href="${app.config.get( "bugs_email", "mailto:galaxy-bugs@bx.psu.edu"  )}">Email comments, bug reports, or suggestions</a></li>
		    <li><a target="_blank" href="${app.config.get( "wiki_url", "http://g2.trac.bx.psu.edu/" )}">Galaxy Wiki</a></li>             
		    <li><a target="_blank" href="${app.config.get( "screencasts_url", "http://g2.trac.bx.psu.edu/wiki/ScreenCasts" )}">Video tutorials (screencasts)</a></li>
		</ul>
	    </div>
	</span>
    
	<span class="tab">
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
		    <li><a target="galaxy_main" href="${h.url_for( controller='user', action='login' )}">Login</a></li>
		    %if app.config.allow_user_creation:
			<li><a target="galaxy_main" href="${h.url_for( controller='user', action='create' )}">Register</a></li>
		    %endif
		</ul>
		<ul class="loggedin-only" style="${style2}">
		    <li>Logged in as <span id="user-email">${user_email}</span></li>
		    <li><a target="galaxy_main" href="${h.url_for( controller='user', action='index' )}">Preferences</a></li>
		    <%
			if app.config.require_login:
			    logout_target = ""
			    logout_url = h.url_for( controller='root', action='index', m_c='user', m_a='logout' )
			else:
			    logout_target = "galaxy_main"
			    logout_url = h.url_for( controller='user', action='logout' )
		    %>
		    <li><a target="${logout_target}" href="${logout_url}">Logout</a></li>
		</ul>
	    </div>
	</span>
	
    </div>
    </div>
    
</%def>

## Messagebox
<%def name="message_box_content()">
</%def>

## Document
<html lang="en">

    ${self.init()}    
    
    <head>
	   <title>${self.title()}</title>
	   ${self.javascripts()}
	   ${self.stylesheets()}
    </head>
    
    <body scroll="no">
        ## Background displays first
        <div id="background"></div>
        ## Layer iframes over backgrounds
        <div id="masthead">
            ${self.masthead()}
        </div>
        <div id="messagebox" class="panel-${self.message_box_class}-message">
            %if self.message_box_visible:
                ${self.message_box_content()}
            %endif
        </div>
        %if self.has_left_panel:
            <div id="left">
                ${self.left_panel()}
            </div>
            <div id="left-border">
                <div id="left-border-inner" style="display: none;"></div>
            </div>
        %endif
        <div id="center">
            ${self.center_panel()}
        </div>
        %if self.has_right_panel:
            <div id="right-border"><div id="right-border-inner" style="display: none;"></div></div>
            <div id="right">
                ${self.right_panel()}
            </div>
        %endif
        ## Allow other body level elements
        ${next.body()}
    </body>
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${self.late_javascripts()}
</html>
