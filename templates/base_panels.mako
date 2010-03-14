## This needs to be on the first line, otherwise IE6 goes into quirks mode
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<%
    self.has_left_panel=True
    self.has_right_panel=True
    self.message_box_visible=False
    self.overlay_visible=False
    self.message_box_class=""
    self.active_view=None
    self.body_class=""
%>
    
<%def name="init()">
    ## Override
</%def>

## Default title
<%def name="title()">Galaxy</%def>

## Default stylesheets
<%def name="stylesheets()">
    ${h.css('base','panel_layout')}
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
    ${h.js( 'IE7', 'ie7-recalc' )}
    <![endif]-->
    ${h.js( 'jquery' )}
</%def>

## Default late-load javascripts
<%def name="late_javascripts()">
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${h.js( 'jquery.event.drag', 'jquery.event.hover', 'jquery.form', 'galaxy.base', 'galaxy.panels' )}
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
    
    </script>
    ## Handle AJAX (actually hidden iframe) upload tool
    <![if !IE]>
    <script type="text/javascript">
        var upload_form_error = function( msg ) {
            if ( ! $("iframe#galaxy_main").contents().find("body").find("div[class='errormessage']").size() ) {
                $("iframe#galaxy_main").contents().find("body").prepend( '<div class="errormessage" name="upload_error">' + msg + '</div><p/>' );
            } else {
                $("iframe#galaxy_main").contents().find("body").find("div[class='errormessage']").text( msg );
            }
        }
        jQuery( function() {
            $("iframe#galaxy_main").load( function() {
                $(this).contents().find("form").each( function() { 
                    if ( $(this).find("input[galaxy-ajax-upload]").length > 0 ){
                        $(this).submit( function() {
                            // Only bother using a hidden iframe if there's a file (e.g. big data) upload
                            var file_upload = false;
                            $(this).find("input[galaxy-ajax-upload]").each( function() {
                                if ( $(this).val() != '' ) {
                                    file_upload = true;
                                }
                            });
                            if ( ! file_upload ) {
                                return true;
                            }
                            // Make a synchronous request to create the datasets first
                            var async_datasets;
                            var upload_error = false;
                            $.ajax( {
                                async:      false,
                                type:       "POST",
                                url:        "${h.url_for(controller='/tool_runner', action='upload_async_create')}",
                                data:       $(this).formSerialize(),
                                dataType:   "json",
                                success:    function(array_obj, status) {
                                                if (array_obj.length > 0) {
                                                    if (array_obj[0] == 'error') {
                                                        upload_error = true;
                                                        upload_form_error(array_obj[1]);
                                                    } else {
                                                        async_datasets = array_obj.join();
                                                    }
                                                } else {
                                                    // ( gvk 1/22/10 ) FIXME: this block is never entered, so there may be a bug somewhere
                                                    // I've done some debugging like checking to see if array_obj is undefined, but have not
                                                    // tracked down the behavior that will result in this block being entered.  I believe the
                                                    // intent was to have this block entered if the upload button is clicked on the upload
                                                    // form but no file was selected.
                                                    upload_error = true;
                                                    upload_form_error( 'No data was entered in the upload form.  You may choose to upload a file, paste some data directly in the data box, or enter URL(s) to fetch data.' );
                                                }
                                            }
                            } );
                            if (upload_error == true) {
                                return false;
                            } else {
                                $(this).find("input[name=async_datasets]").val( async_datasets );
                                $(this).append("<input type='hidden' name='ajax_upload' value='true'>");
                            }
                            // iframe submit is required for nginx (otherwise the encoding is wrong)
                            $(this).ajaxSubmit( { iframe: true } );
                            if ( $(this).find("input[name='folder_id']").val() != undefined ) {
                                var library_id = $(this).find("input[name='library_id']").val();
                                var show_deleted = $(this).find("input[name='show_deleted']").val();
                                if ( location.pathname.indexOf( 'admin' ) != -1 ) {
                                    $("iframe#galaxy_main").attr("src","${h.url_for( controller='library_common', action='browse_library' )}?cntrller=library_admin&id=" + library_id + "&created_ldda_ids=" + async_datasets + "&show_deleted=" + show_deleted);
                                } else {
                                    $("iframe#galaxy_main").attr("src","${h.url_for( controller='library_common', action='browse_library' )}?cntrller=library&id=" + library_id + "&created_ldda_ids=" + async_datasets + "&show_deleted=" + show_deleted);
                                }
                            } else {
                                $("iframe#galaxy_main").attr("src","${h.url_for(controller='tool_runner', action='upload_async_message')}");
                            }
                            return false;
                        });
                    }
                });
            });
        });
    </script>
    <![endif]>
</%def>

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
    
    %if trans.user and trans.request_types():
        <td class="tab">
            <a>Lab</a>
            <div class="submenu">
            <ul>            
                <li><a href="${h.url_for( controller='/requests', action='index' )}">Sequencing Requests</a></li>
                <li><a target="_blank" href="${app.config.get( "lims_doc_url", "http://main.g2.bx.psu.edu/u/rc/p/sts" )}">Help</a></li>
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
            <li><a href="${h.url_for( controller='/tracks', action='index' )}">Build track browser</a></li>
            <li><hr style="color: inherit; background-color: gray"/></li>
	    <li><a href="${h.url_for( controller='/visualization', action='list' )}">Stored visualizations</a></li>
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
            <li><a href="${h.url_for( controller='/user', action='login' )}">Login</a></li>
            %if app.config.allow_user_creation:
            <li><a href="${h.url_for( controller='/user', action='create' )}">Register</a></li>
            %endif
        </ul>
        <ul class="loggedin-only" style="${style2}">
            %if app.config.use_remote_user:
                %if app.config.remote_user_logout_href:
                    <li><a href="${app.config.remote_user_logout_href}" target="_top">Logout</a></li>
                %endif
            %else:
                <li>Logged in as <span id="user-email">${user_email}</span></li>
                <li><a target="galaxy_main" href="${h.url_for( controller='/user', action='index' )}">Preferences</a></li>
                <%
                    if app.config.require_login:
                        logout_target = ""
                        logout_url = h.url_for( controller='/root', action='index', m_c='user', m_a='logout' )
                    else:
                        logout_target = ""
                        logout_url = h.url_for( controller='/user', action='logout' )
                %>
                <li><a target="${logout_target}" href="${logout_url}">Logout</a></li>
                <li><hr style="color: inherit; background-color: gray"/></li>
                <li><a target="galaxy_main" href="${h.url_for( controller='/history', action='list' )}">Histories</a></li>
                <li><a target="galaxy_main" href="${h.url_for( controller='/dataset', action='list' )}">Datasets</a></li>
                %if app.config.get_bool( 'enable_pages', False ):
                    <li><a href="${h.url_for( controller='/page', action='list' )}">Pages</a></li>  
                %endif
            %endif
        </ul>
        </div>
    </td>
    
    </tr>
    </table>
    
    </div>
    
    ## Logo, layered over tabs to be clickable
    <div class="title" style="position: absolute; top: 0; left: 0;">
        <a href="/">
        <img border="0" src="${h.url_for('/static/images/galaxyIcon_noText.png')}" style="width: 26px; vertical-align: top;">
        Galaxy
        %if app.config.brand:
        <span class='brand'>/${app.config.brand}</span>
        %endif
        </a>
    </div>
    
</%def>

<%def name="overlay( title='', content='' )">
    <%def name="title()"></%def>
    <%def name="content()"></%def>

    <div id="overlay"
    %if not self.overlay_visible:
    style="display: none;"
    %endif
    >
    ##
    <div id="overlay-background" style="position: absolute; width: 100%; height: 100%;"></div>
    
    ## Need a table here for centering in IE6
    <table class="dialog-box-container" border="0" cellpadding="0" cellspacing="0"
    %if not self.overlay_visible:
        style="display: none;"
    %endif
    ><tr><td>
    <div class="dialog-box-wrapper">
        <div class="dialog-box">
        <div class="unified-panel-header">
            <div class="unified-panel-header-inner"><span class='title'>${title}</span></div>
        </div>
        <div class="body">${content}</div>
        <div>
            <div class="buttons" style="display: none; float: right;"></div>
            <div class="extra_buttons" style="display: none; padding: 5px;"></div>
            <div style="clear: both;"></div>
        </div>
        </div>
    </div>
    </td></tr></table>
    </div>
</%def>

## Messagebox
<%def name="message_box_content()">
</%def>

## Document
<html>
    ${self.init()}    
    <head>
    <title>${self.title()}</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    ${self.stylesheets()}
    ${self.javascripts()}
    </head>
    
    <body scroll="no" class="${self.body_class}">
	<div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; min-width: 600px;">
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
    ${self.overlay()}
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
	</div>
        ## Allow other body level elements
    </body>
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${self.late_javascripts()}
</html>
