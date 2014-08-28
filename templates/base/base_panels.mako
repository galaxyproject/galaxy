<!DOCTYPE HTML>
<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />

<%
    self.has_left_panel = hasattr( self, 'left_panel' )
    self.has_right_panel = hasattr( self, 'right_panel' )
    self.message_box_visible = app.config.message_box_visible
    self.show_inactivity_warning = False
    if trans.webapp.name == 'galaxy' and trans.user:
        self.show_inactivity_warning = ( ( trans.user.active is False ) and ( app.config.user_activation_on ) and ( app.config.inactivity_box_content is not None ) )
    self.overlay_visible=False
    self.active_view=None
    self.body_class=""
    self.require_javascript=False
%>
    
<%def name="init()">
    ## Override
</%def>

## Default stylesheets
<%def name="stylesheets()">
    ${h.css(
        'base',
        'jquery.rating'
    )}
    <style type="text/css">
    #center {
        %if not self.has_left_panel:
            left: 0 !important;
        %endif
        %if not self.has_right_panel:
            right: 0 !important;
        %endif
    }
    </style>
</%def>

## Default javascripts
<%def name="javascripts()">

    ## Send errors to Sntry server if configured
    %if app.config.sentry_dsn:
        ${h.js( "libs/tracekit", "libs/raven" )}
        <script>
            Raven.config('${app.config.sentry_dsn_public}').install();
            %if trans.user:
                Raven.setUser( { email: "${trans.user.email}" } );
            %endif
        </script>
    %endif

    ${h.js(
        'libs/jquery/jquery',
        'libs/jquery/jquery.migrate',
        'libs/jquery/select2',
        'libs/bootstrap',
        'libs/underscore',
        'libs/backbone/backbone',
        'libs/handlebars.runtime',
        'galaxy.base',
        'libs/require',
        "mvc/ui"
    )}
    
    <script type="text/javascript">
        ## global configuration object
        var galaxy_config =
        {
            root: '${h.url_for( "/" )}'
        };

        //## load additional style sheet
        //if (window != window.top)
        //    $('<link href="' + galaxy_config.root + 'static/style/galaxy.frame.masthead.css" rel="stylesheet">').appendTo('head');

        // console protection
        window.console = window.console || {
            log     : function(){},
            debug   : function(){},
            info    : function(){},
            warn    : function(){},
            error   : function(){},
            assert  : function(){}
        };

        ## configure require
        require.config({
            baseUrl: "${h.url_for('/static/scripts') }",
            shim: {
                "libs/underscore": { exports: "_" },
                "libs/backbone/backbone": { exports: "Backbone" }
            }
        });
    </script>

</%def>

<%def name="javascript_app()">
    ## load the Galaxy global js var
    ${ galaxy_client.load() }
</%def>

## Default late-load javascripts
<%def name="late_javascripts()">
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${h.js(
        'libs/jquery/jquery.event.hover',
        'libs/jquery/jquery.form',
        'libs/jquery/jquery.rating',
        'galaxy.panels'
    )}
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
    <script type="text/javascript">
        var upload_form_error = function( msg ) {
            var $galaxy_mainBody = $("iframe#galaxy_main").contents().find("body"),
                $errMsg = $galaxy_mainBody.find( 'div.errormessage' );
            if ( !$errMsg.size() ){
                $errMsg = $( '<div/>' ).addClass( 'errormessage' ).prependTo( $galaxy_mainBody );
            }
            $errMsg.text( msg );
        }

        var uploads_in_progress = 0;
        function decrementUploadsInProgress(){
            uploads_in_progress -= 1;
            if( uploads_in_progress === 0 ){
                window.onbeforeunload = null;
            }
        }
        jQuery( function() {
            $("iframe#galaxy_main").load( function() {
                $(this).contents().find("form").each( function() {
                    if ( $(this).find("input[galaxy-ajax-upload]").length > 0 ){
                        var $form = $( this );

                        $(this).submit( function( event ) {
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

                            //NOTE: in order for upload.py to match the datasets created below, we'll move the js File
                            //  object's name into the file_data field (not in the form only for what we send to
                            //  upload_async_create)
                            var formData = $( this ).serializeArray();
                            var name = function(){
                                var $fileInput = $form.find( 'input[name="files_0|file_data"]' );
                                if( /msie/.test( navigator.userAgent.toLowerCase() ) ){
                                    return $fileInput.val().replace( 'C:\\fakepath\\', '' );
                                } else {
                                    return $fileInput.get( 0 ).files[0].name;
                                }
                            }
                            formData.push({ name: "files_0|file_data", value: name });

                            $.ajax( {
                                async:      false,
                                type:       "POST",
                                url:        "${h.url_for(controller='/tool_runner', action='upload_async_create')}",
                                data:       formData,
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

                            // show the dataset we created above in the history panel
                            Galaxy && Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.refreshContents();

                            if (upload_error == true) {
                                return false;
                            } else {
                                $(this).find("input[name=async_datasets]").val( async_datasets );
                                $(this).append("<input type='hidden' name='ajax_upload' value='true'>");
                            }
                            // iframe submit is required for nginx (otherwise the encoding is wrong)
                            $(this).ajaxSubmit({
                                //iframe: true,
                                error: function( xhr, msg, status ){
                                    decrementUploadsInProgress();
                                },
                                success: function ( response, x, y, z ) {
                                    decrementUploadsInProgress();
                                }
                            });
                            uploads_in_progress++;
                            window.onbeforeunload = function() {
                                return "Navigating away from the Galaxy analysis interface will interrupt the "
                                        + "file upload(s) currently in progress.  Do you really want to do this?";
                            }
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
                            event.preventDefault();
                            return false;
                        });
                    }
                });
            });
        });
    </script>
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

    <div id="top-modal" class="modal fade ${overlay_class}" ${display}>
        <div id="top-modal-backdrop" class="modal-backdrop fade ${overlay_class}" style="z-index: -1"></div>
        <div id="top-modal-dialog" class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type='button' class='close' style="display: none;">&times;</button>
                    <h4 class='title'>${title}</h4>
                </div>
                <div class="modal-body">${content}</div>
                <div class="modal-footer">
                    <div class="buttons" style="float: right;"></div>
                    <div class="extra_buttons" style=""></div>
                    <div style="clear: both;"></div>
                </div>
            </div>
        </div>
    </div>
</%def>

## Document
<html>
    <!--base_panels.mako-->
    ${self.init()}    
    <head>
        %if app.config.brand:
            <title>${self.title()} / ${app.config.brand}</title>
        %else:
            <title>${self.title()}</title>
        %endif
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ## For mobile browsers, don't scale up
        <meta name = "viewport" content = "maximum-scale=1.0">
        ## Force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">
        ${self.stylesheets()}
        ${self.javascripts()}
        ${self.javascript_app()}
    </head>
    
    <%
    body_class = self.body_class
    if self.message_box_visible:
        body_class += " has-message-box"
    if self.show_inactivity_warning:
        body_class += " has-inactivity-box"
    %>

    <body scroll="no" class="full-content ${body_class}">
        %if self.require_javascript:
            <noscript>
                <div class="overlay overlay-background">
                    <div class="modal dialog-box" border="0">
                        <div class="modal-header"><h3 class="title">Javascript Required</h3></div>
                        <div class="modal-body">The Galaxy analysis interface requires a browser with Javascript enabled. <br> Please enable Javascript and refresh this page</div>
                    </div>
                </div>
            </noscript>
        %endif
        <div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
            ## Background displays first
            <div id="background"></div>
            ## Layer iframes over backgrounds
            <div id="masthead" class="navbar navbar-fixed-top navbar-inverse">
                ${self.masthead()}
            </div>
            <div id="messagebox" class="panel-${app.config.message_box_class}-message">
                ${app.config.message_box_content}
            </div>
            %if self.show_inactivity_warning:
                <div id="inactivebox" class="panel-warning-message">
                    ${app.config.inactivity_box_content} <a href="${h.url_for( controller='user', action='resend_verification' )}">Resend verification.</a>
                </div>
            %endif
            ${self.overlay(visible=self.overlay_visible)}
            %if self.has_left_panel:
                <div id="left">
                    ${self.left_panel()}
                    <div class="unified-panel-footer">
                        <div class="panel-collapse"></div>
                        <div class="drag"></div>
                    </div>
                </div><!--end left-->
            %endif
            <div id="center" class="inbound">
                ${self.center_panel()}
            </div><!--end center-->
            %if self.has_right_panel:
                <div id="right">
                    ${self.right_panel()}
                    <div class="unified-panel-footer">
                        <div class="panel-collapse right"></div>
                        <div class="drag"></div>
                    </div>
                </div><!--end right-->
            %endif
        </div><!--end everything-->
        ## Allow other body level elements
    </body>
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${self.late_javascripts()}
</html>
