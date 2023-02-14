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
    ${h.dist_css('base')}
</%def>

## Default javascripts
## TODO: remove when all libs are required directly in modules
<%def name="javascripts()">
    ${ h.dist_js(
        'libs.bundled',
        'generic.bundled'
    )}
</%def>

<%def name="javascript_app()">
    ${ galaxy_client.load() }
</%def>

## Default late-load javascripts
<%def name="late_javascripts()">
    %if t.webapp.name == 'galaxy' and app.config.ga_code:
        ${galaxy_client.config_google_analytics(app.config.ga_code)}
    %endif
    %if t.webapp.name == 'galaxy' and app.config.plausible_server and app.config.plausible_domain:
        ${ galaxy_client.config_plausible_analytics(app.config.plausible_server, app.config.plausible_domain) }
    %endif
    %if t.webapp.name == 'galaxy' and app.config.matomo_server and app.config.matomo_site_id:
        ${ galaxy_client.config_matomo_analytics(app.config.matomo_server, app.config.matomo_site_id) }
    %endif

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

    <div id="top-modal" class="modal ${overlay_class}" ${display}>
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
    ${self.init()}
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />

        <title>
            Galaxy
            %if app.config.brand:
            | ${app.config.brand}
            %endif
            | ${self.title()}
        </title>

        ## relative href for site root
        <link rel="index" href="${ h.url_for( '/' ) }"/>
        
        ${self.stylesheets()}

        ## Normally, we'd put all the javascripts at the bottom of the <body>
        ## but during this transitional period we need access to the config
        ## functions which are only available when these scripts are executed
        ## and I can't yet control when the templates are going to write scripts
        ## to the output
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
        <div id="everything">
            
            ## Background displays first
            <div id="background"></div>
            
            ## Layer iframes over backgrounds
            <div id="masthead" class="navbar navbar-fixed-top navbar-inverse">
                ${self.masthead()}
            </div>
            
            %if self.message_box_visible:
                <div id="messagebox" class="alert alert-${app.config.message_box_class} rounded-0 m-0 p-2">
                    ${app.config.message_box_content}
                </div>
            %endif
            
            %if self.show_inactivity_warning:
                <div id="inactivebox" class="alert alert-warning rounded-0 m-0 p-2">
                    ${app.config.inactivity_box_content} <a href="${h.url_for( controller='user', action='resend_verification' )}">Resend verification.</a>
                </div>
            %endif
            
            ${self.overlay(visible=self.overlay_visible)}
            
            <div id="columns">
                %if self.has_left_panel:
                    <div id="left">
                        ${self.left_panel()}
                        <div class="unified-panel-footer">
                            <div id="left-panel-collapse" class="panel-collapse left"></div>
                            <div id="left-panel-drag" class="drag"></div>
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
                            <div id="right-panel-collapse" class="panel-collapse right"></div>
                            <div id="right-panel-drag" class="drag"></div>
                        </div>
                    </div><!--end right-->
                %endif
            </div><!--end columns-->
        </div><!--end everything-->

        <div id='dd-helper' style="display: none;"></div>
        ## Allow other body level elements
        ## Scripts can be loaded later since they progressively add features to
        ## the panels, but do not change layout
        ${self.late_javascripts()}
    </body>
</html>
