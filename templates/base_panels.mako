<!DOCTYPE HTML>

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

## Default stylesheets
<%def name="stylesheets()">
    ${h.css('base','panel_layout','jquery.rating')}
    <style type="text/css">
    body, html {
        overflow: hidden;
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
    }
    #center {
        %if not self.has_left_panel:
            left: 0 !important;
        %endif
        %if not self.has_right_panel:
            right: 0 !important;
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
    ${h.js( 'jquery', 'libs/underscore', 'libs/backbone', 'libs/backbone-relational', 'libs/handlebars.runtime', 'mvc/ui' )}
    <script type="text/javascript">
        // Set up needed paths.
        var galaxy_paths = new GalaxyPaths({
            root_path: '${h.url_for( "/" )}',
            image_path: '${h.url_for( "/static/images" )}'
        });
    </script>
</%def>

## Default late-load javascripts
<%def name="late_javascripts()">
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${h.js( 'jquery.event.drag', 'jquery.event.hover', 'jquery.form', 'jquery.rating', 'galaxy.base', 'galaxy.panels' )}
    <script type="text/javascript">
        
    ensure_dd_helper();
        
    %if self.has_left_panel:
            var lp = new Panel( { panel: $("#left"), center: $("#center"), drag: $("#left > .unified-panel-footer > .drag" ), toggle: $("#left > .unified-panel-footer > .panel-collapse" ) } );
            force_left_panel = function( x ) { lp.force_panel( x ) };
        %endif
        
    %if self.has_right_panel:
            var rp = new Panel( { panel: $("#right"), center: $("#center"), drag: $("#right > .unified-panel-footer > .drag" ), toggle: $("#right > .unified-panel-footer > .panel-collapse" ), right: true } );
            window.handle_minwidth_hint = function( x ) { rp.handle_minwidth_hint( x ) };
            force_right_panel = function( x ) { rp.force_panel( x ) };
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
        var uploads_in_progress = 0;
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
                            $(this).ajaxSubmit( { iframe:   true,
                                                  complete: function (xhr, stat) {
                                                                uploads_in_progress--;
                                                                if (uploads_in_progress == 0) {
                                                                    window.onbeforeunload = null;
                                                                }
                                                            }
                                                 } );
                            uploads_in_progress++;
                            window.onbeforeunload = function() { return "Navigating away from the Galaxy analysis interface will interrupt the file upload(s) currently in progress.  Do you really want to do this?"; }
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
    ## Override
</%def>

<%def name="overlay( title='', content='', visible=False )">
    <%def name="title()"></%def>
    <%def name="content()"></%def>

    <%
    if visible:
        display = "style='display: block;'"
        overlay_class = "in"
    else:
        display = "style='display: none;'"
        overlay_class = ""
    %>

    <div id="overlay" ${display}>

        <div id="overlay-background" class="modal-backdrop fade ${overlay_class}"></div>

        <div id="dialog-box" class="modal dialog-box" border="0" ${display}>
                <div class="modal-header">
                    <span><h3 class='title'>${title}</h3></span>
                </div>
                <div class="modal-body">${content}</div>
                <div class="modal-footer">
                    <div class="buttons" style="float: right;"></div>
                    <div class="extra_buttons" style=""></div>
                    <div style="clear: both;"></div>
                </div>
        </div>
    
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
        ## For mobile browsers, don't scale up
        <meta name = "viewport" content = "maximum-scale=1.0">
        ## Force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">
        ${self.stylesheets()}
        ${self.javascripts()}
    </head>
    
    <body scroll="no" class="${self.body_class}">
        <div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; min-width: 600px;">
            ## Background displays first
            <div id="background"></div>
            ## Layer iframes over backgrounds
            <div id="masthead" class="navbar navbar-fixed-top">
                <div class="masthead-inner navbar-inner">
                    <div class="container">${self.masthead()}</div>
                </div>
            </div>
            <div id="messagebox" class="panel-${self.message_box_class}-message">
                %if self.message_box_visible:
                    ${self.message_box_content()}
                %endif
            </div>
            ${self.overlay(visible=self.overlay_visible)}
            %if self.has_left_panel:
                <div id="left">
                    ${self.left_panel()}
                    <div class="unified-panel-footer">
                        <div class="panel-collapse"></span></div>
                        <div class="drag"></div>
                    </div>
                </div>
            %endif
            <div id="center">
                ${self.center_panel()}
            </div>
            %if self.has_right_panel:
                <div id="right">
                    ${self.right_panel()}
                    <div class="unified-panel-footer">
                        <div class="panel-collapse right"></span></div>
                        <div class="drag"></div>
                    </div>
                </div>
            %endif
        </div>
        ## Allow other body level elements
    </body>
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${self.late_javascripts()}
</html>
