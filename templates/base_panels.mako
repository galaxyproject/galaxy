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
    <script type="text/javascript">
        var image_path = '${h.url_for("/static/images")}';
    </script>
    ${h.js( 'jquery' )}
</%def>

## Default late-load javascripts
<%def name="late_javascripts()">
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${h.js( 'jquery.event.drag', 'jquery.event.hover', 'jquery.form', 'jquery.rating', 'galaxy.base', 'galaxy.panels' )}
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
    ## Override
</%def>

<%def name="overlay( title='', content='', visible=False )">
    <%def name="title()"></%def>
    <%def name="content()"></%def>

    <div id="overlay"
    %if not visible:
        style="display: none;"
    %endif
    >
    ##
    <div id="overlay-background" style="position: absolute; width: 100%; height: 100%;"></div>
    
    ## Need a table here for centering in IE6
    <table class="dialog-box-container" border="0" cellpadding="0" cellspacing="0"
    %if not visible:
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
        <meta name = "viewport" content = "maximum-scale=1.0">
        ${self.stylesheets()}
        ${self.javascripts()}
    </head>
    
    <body scroll="no" class="${self.body_class}">
        <div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; min-width: 600px;">
            ## Background displays first
            <div id="background"></div>
            ## Layer iframes over backgrounds
            <div id="masthead" class="navbar nabbar-fixed-top">
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
