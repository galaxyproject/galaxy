<!DOCTYPE HTML>
<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />

<%
    self.has_left_panel = hasattr( self, 'left_panel' )
    self.has_right_panel = hasattr( self, 'right_panel' )
    self.message_box_visible = app.config.message_box_visible
    self.show_inactivity_warning = False
    if trans.webapp.name == 'galaxy' and trans.user:
        self.show_inactivity_warning = ( ( trans.user.active is False ) and ( app.config.user_activation_on ) )
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
        'jquery.rating',
        'bootstrap-tour'
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
    ## Send errors to Sentry server if configured
    %if app.config.sentry_dsn:
        ${h.js( "libs/raven" )}
        <script>
            Raven.config('${app.config.sentry_dsn_public}').install();
            %if trans.user:
                Raven.setUser( { email: "${trans.user.email | h}" } );
            %endif
        </script>
    %endif

    ${h.js(
        ## TODO: remove when all libs are required directly in modules
        'bundled/libs.bundled',
        'libs/require',
    )}

    <script type="text/javascript">
        // configure require
        // due to our using both script tags and require, we need to access the same jq in both for plugin retention
        // source http://www.manuel-strehl.de/dev/load_jquery_before_requirejs.en.html
        window.Galaxy = window.Galaxy || {};
        window.Galaxy.root = '${h.url_for( "/" )}';
        define( 'jquery', [], function(){ return jQuery; })
        // TODO: use one system

        // shims and paths
        require.config({
            baseUrl: "${h.url_for('/static/scripts') }",
            shim: {
                "libs/underscore": {
                    exports: "_"
                },
                "libs/backbone": {
                    deps: [ 'jquery', 'libs/underscore' ],
                    exports: "Backbone"
                }
            },
            // cache busting using time server was restarted
            urlArgs: 'v=${app.server_starttime}',
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
    <script type="text/javascript">

    %if self.has_left_panel:
        var lp = new panels.LeftPanel({ el: '#left' });
        force_left_panel = function( x ) { lp.force_panel( x ) };
    %endif

    %if self.has_right_panel:
        var rp = new panels.RightPanel({ el: '#right' });
        window.handle_minwidth_hint = function( x ) { rp.handle_minwidth_hint( x ) };
        force_right_panel = function( x ) { rp.force_panel( x ) };
    %endif

    %if t.webapp.name == 'galaxy' and app.config.ga_code:
          (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
          (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
          m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
          })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
          ga('create', '${app.config.ga_code}', 'auto');
          ga('send', 'pageview');
    %endif

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
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ## For mobile browsers, don't scale up
        <meta name = "viewport" content = "maximum-scale=1.0">
        ## Force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">

        %if app.config.brand:
            <title>${self.title()} / ${app.config.brand}</title>
        %else:
            <title>${self.title()}</title>
        %endif
        ## relative href for site root
        <link rel="index" href="${ h.url_for( '/' ) }"/>
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
            %if self.message_box_visible:
                <div id="messagebox" class="panel-${app.config.message_box_class}-message" style="display:block">
                    ${app.config.message_box_content}
                </div>
            %endif
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
        <div id='dd-helper' style="display: none;"></div>
        ## Allow other body level elements
        ## Scripts can be loaded later since they progressively add features to
        ## the panels, but do not change layout
        ${self.late_javascripts()}
    </body>
</html>
