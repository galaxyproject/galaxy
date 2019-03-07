<%namespace name="masthead" file="/webapps/galaxy/galaxy.masthead.mako"/>
<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />

<!DOCTYPE html>

## inject parameters parsed by controller config dictionary
<%
    ## set defaults
    self.galaxy_config = {
        ## template options
        'title'         : 'Galaxy - Data Intensive Biology for Everyone',
        'master'        : True,
        'left_panel'    : False,
        'right_panel'   : False,
        'message_box'   : False,

        ## root
        'root'          : h.url_for("/"),

        ## inject app specific configuration
        'app'           : config['app']
    }

    ## update configuration
    self.galaxy_config.update(config)
%>

<html>
    <head>
        <meta charset="UTF-8">
        ## for mobile browsers, don't scale up
        <meta name = "viewport" content = "maximum-scale=1.0">
        ## force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="x-ua-compatible" content="ie=edge,chrome=1">

        <title>
            Galaxy
            %if app.config.brand:
            | ${app.config.brand}
            %endif
            %if self.galaxy_config['title']:
            | ${self.galaxy_config['title']}
            %endif
        </title>

        ${self.stylesheets()}
        ${self.javascripts()}
        ${self.javascript_app()}

    </head>

    <body scroll="no" class="full-content">
        <div id="everything">
            
            <div id="background"></div>

            %if self.galaxy_config['master']:
                <div id="masthead" class="navbar navbar-fixed-top navbar-inverse"></div>
                ${masthead.load()}
            %endif

            ${self.message_box()}

            <div id="columns">
                ${self.left_panel()}
                ${self.center_panel()}
                ${self.right_panel()}
            </div>

        </div>

        <div id='dd-helper' style="display: none;"></div>

        ${self.late_javascripts()}

    </body>
</html>

<%def name="message_box()">
    %if self.galaxy_config['message_box']:
        <div id="messagebox" class="panel-message"></div>
        <style>
            #left, #left-border, #center, #right-border, #right {
                top: 64px;
            }
        </style>
    %endif
</%def>

<%def name="left_panel()">
    %if self.galaxy_config['left_panel']:
        <div id="left">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">
                    <div class="unified-panel-icons"></div>
                    <div class="unified-panel-title"></div>
                </div>
            </div>
            <div class="unified-panel-body"></div>
            <div class="unified-panel-footer">
                <div id="left-panel-collapse" class="panel-collapse right"></span></div>
                <div id="left-panel-drag" class="drag"></div>
            </div>
        </div>
    %endif
</%def>

<%def name="right_panel()">
    %if self.galaxy_config['right_panel']:
        <div id="right">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">
                    <div class="unified-panel-icons"></div>
                    <div class="unified-panel-title"></div>
                </div>
            </div>
            <div class="unified-panel-body"></div>
            <div class="unified-panel-footer">
                <div id="right-panel-collapse" class="panel-collapse right"></span></div>
                <div id="right-panel-drag" class="drag"></div>
            </div>
        </div>
    %endif
</%def>

<%def name="center_panel()">
    <div id="center">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="unified-panel-title"></div>
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="unified-panel-body"></div>
    </div>
</%def>

<%def name="stylesheets()">

    <!-- galaxy.panels.mako stylesheets -->

    ## load default style
    ${h.css("base")}

    <style type="text/css">

        #everything {
            position: absolute; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%;
        }

        #left .unified-panel-icons,
        #right .unified-panel-icons {
            float: right;
        }

        #left .unified-panel-body,
        #right .unified-panel-body {
            overflow: auto;
        }

        #center .unified-panel-title {
            float: left;
        }

    </style>

</%def>

## TODO: remove when all libs are required directly in modules
<%def name="javascripts()">
    <!-- galaxy.panels.mako javascripts -->
    ${h.js(
        'libs/d3',
        'bundled/libs.chunk',
        'bundled/base.chunk'
    )}
    ${self.javascript_entry()}
</%def>

<%def name="javascript_entry()">
    <!-- galaxy.panels.mako javascript_entry -->
    ${h.js('bundled/generic.bundled')}
</%def>

<%def name="javascript_app()">
    <!-- galaxy.panels.mako javascript_app -->
    <script type="text/javascript">
    
        var galaxyConfig = ${ h.dumps( self.galaxy_config ) };

        ## TODO: Some visualizations (and more?) currently use this config, should be refactored.
        window.galaxy_config = galaxyConfig;

        var panelConfig = Object.assign(galaxyConfig, {
            rightPanelSelector: '#right',
            leftPanelSelector: '#left'
        });

        config.addInitialization(function() {
            console.log("base/base_panels.mako, panel init");
            window.bundleEntries.panelManagement(panelConfig);
        });

        config.addInitialization(function() {
            console.log("base/base_panels.mako, panelConfig init");
            console.log("runs an init function named in python config", panelConfig);
            try {
                var initFn = panelConfig.app.jscript;
                if (initFn in window.bundleEntries) {
                    window.bundleEntries[initFn]();
                } else {
                    console.warn("Requested initialization function missing", initFn);
                }
            } catch(err) {
                console.error("Unable to init panels", err);
                console.trace();
            }
        });

    </script>

    ${ galaxy_client.load() }
    ## ${ galaxy_client.config_sentry(app) }

</%def>

## default late-load javascripts
<%def name="late_javascripts()"></%def>
