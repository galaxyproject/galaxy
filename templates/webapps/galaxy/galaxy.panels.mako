<%namespace name="masthead" file="/webapps/galaxy/galaxy.masthead.mako"/>
<%namespace name="galaxy_client" file="/galaxy_client_app.mako" />

<!DOCTYPE HTML>

## inject parameters parsed by controller config dictionary
<%
    ## set defaults
    self.galaxy_config = {
        ## template options
        'title'         : '',
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

<%def name="javascripts()">

    ## load jscript libraries
    ${h.js(
        'libs/jquery/jquery',
        'libs/jquery/jquery-ui',
        "libs/jquery/select2",
        'libs/bootstrap',
        'libs/underscore',
        'libs/backbone/backbone',
        'libs/require',
        'libs/d3',
        'galaxy.base',
        'galaxy.panels',
        'libs/handlebars.runtime',
        "mvc/ui"
    )}
    
    ## send errors to Sntry server if configured
    %if app.config.sentry_dsn:
        ${h.js( "libs/tracekit", "libs/raven" )}
        <script>
            Raven.config('${app.config.sentry_dsn_public}').install();
            %if trans.user:
                Raven.setUser( { email: "${trans.user.email}" } );
            %endif
        </script>
    %endif
    
    ## make sure console exists
    <script type="text/javascript">
        // console protection
        window.console = window.console ||
        {
            log     : function(){},
            debug   : function(){},
            info    : function(){},
            warn    : function(){},
            error   : function(){},
            assert  : function(){}
        };
    </script>

    ## load default style
    ${h.css("base")}

    ## modify default style
    <style type="text/css">
    #center {
        %if not self.galaxy_config['left_panel']:
            left: 0 !important;
        %endif
            %if not self.galaxy_config['right_panel']:
            right: 0 !important;
        %endif
    }
    %if self.galaxy_config['message_box']:
        #left, #left-border, #center, #right-border, #right
        {
            top: 64px;
        }
    %endif
    </style>
    
    ## default script wrapper
    <script type="text/javascript">
        ## configure require
        require.config({
            baseUrl: "${h.url_for('/static/scripts') }",
            shim: {
                "libs/underscore": { exports: "_" },
                "libs/d3": { exports: "d3" },
                "libs/backbone/backbone": { exports: "Backbone" },
            }
        });
        var galaxy_config = ${ h.dumps( self.galaxy_config ) };
        
    </script>
</%def>

<%def name="javascript_app()">
    <script type="text/javascript">
        // load any app configured
        define( 'app', function(){
            var jscript = galaxy_config.app.jscript;
            if( jscript ){
                require([ jscript ], function( js_lib ){
                    $( function(){
                        // load galaxy module application
                        var module = new js_lib.GalaxyApp();
                    });
                });
            } else {
                console.log("'galaxy_config.app.jscript' missing.");
            }
        });
    </script>

    ## load the Galaxy global js var and run 'app' from above
    ${ galaxy_client.load( app='app' ) }

    ## alternate call where the module calls itself when included (no call to GalaxyApp()) - the above won't be needed
    ##precondition: module must call jq onready itself
    ##<% app_config = self.galaxy_config[ 'app' ]; print app_config %>
    ##${ galaxy_client.load( app=( app_config[ 'jscript' ] if 'jscript' in app_config else None )) }
    
    ##TODO: at that point, we can think about optimizing the various apps
</%def>

## default late-load javascripts
<%def name="late_javascripts()">
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    <script type="text/javascript">
        
        ensure_dd_helper();
        
        ## configure left panel
        %if self.galaxy_config['left_panel']:
            var lp = new Panel( { panel: $("#left"), center: $("#center"), drag: $("#left > .unified-panel-footer > .drag" ), toggle: $("#left > .unified-panel-footer > .panel-collapse" ) } );
            force_left_panel = function( x ) { lp.force_panel( x ) };
        %endif
        
        ## configure right panel
        %if self.galaxy_config['right_panel']:
            var rp = new Panel( { panel: $("#right"), center: $("#center"), drag: $("#right > .unified-panel-footer > .drag" ), toggle: $("#right > .unified-panel-footer > .panel-collapse" ), right: true } );
            window.handle_minwidth_hint = function( x ) { rp.handle_minwidth_hint( x ) };
            force_right_panel = function( x ) { rp.force_panel( x ) };
        %endif
    </script>
</%def>

## document
<html>
    <head>
        <title></title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        
        ## for mobile browsers, don't scale up
        <meta name = "viewport" content = "maximum-scale=1.0">
        
        ## force IE to standards mode, and prefer Google Chrome Frame if the user has already installed it
        <meta http-equiv="X-UA-Compatible" content="IE=Edge,chrome=1">
 
        ## load scripts
        ${self.javascripts()}
        ${self.javascript_app()}
    </head>
    
    <body scroll="no" class="full-content">
        <div id="everything" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
            ## background displays first
            <div id="background"></div>
            
            ## master header
            %if self.galaxy_config['master']:
                ${masthead.load()}
            %endif
            
            ## message box
            %if self.galaxy_config['message_box']:
                <div id="messagebox" class="panel-message"></div>
            %endif
            ## left panel
            %if self.galaxy_config['left_panel']:
                <div id="left">
                    <div class="unified-panel-header" unselectable="on">
                        <div class="unified-panel-header-inner">
                            <div class="unified-panel-icons" style="float: right"></div>
                            <div class="unified-panel-title"></div>
                        </div>
                    </div>
                    <div class="unified-panel-body" style="overflow: auto;"></div>
                    <div class="unified-panel-footer">
                        <div class="panel-collapse right"></span></div>
                        <div class="drag"></div>
                    </div>
                </div>
            %endif
            
            ## center panel
            <div id="center">
                <div class="unified-panel-header" unselectable="on">
                    <div class="unified-panel-header-inner">
                        <div class="unified-panel-title" style="float:left;"></div>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="unified-panel-body"></div>
            </div>
            
            ## right panel
            %if self.galaxy_config['right_panel']:
                <div id="right">
                    <div class="unified-panel-header" unselectable="on">
                        <div class="unified-panel-header-inner">
                            <div class="unified-panel-icons" style="float: right"></div>
                            <div class="unified-panel-title"></div>
                        </div>
                    </div>
                    <div class="unified-panel-body" style="overflow: auto;"></div>
                    <div class="unified-panel-footer">
                        <div class="panel-collapse right"></span></div>
                        <div class="drag"></div>
                    </div>
                </div>
            %endif
        </div>
    </body>
    ## Scripts can be loaded later since they progressively add features to
    ## the panels, but do not change layout
    ${self.late_javascripts()}
</html>
