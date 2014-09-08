<%
    root        = h.url_for( "/" )
    app_root    = root + "plugins/visualizations/charts/static/"
%>


<!DOCTYPE HTML>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>${hda.name} | ${visualization_name}</title>

        ## install shared libraries
        ${h.js( 'libs/jquery/jquery',
                'libs/bootstrap',
                'libs/require',
                'libs/underscore',
                'libs/backbone/backbone',
                'libs/d3')}

        ## shared css
        ${h.css( 'base' )}

        ## crossfilter
        ${h.javascript_link( app_root + "plugins/crossfilter/crossfilter.js" )}

        ## canvg
        ${h.javascript_link( app_root + "plugins/canvg/rgbcolor.js" )}
        ${h.javascript_link( app_root + "plugins/canvg/canvg.js" )}

        ## nvd3
        ${h.stylesheet_link( app_root + "plugins/nvd3/nv.d3.css" )}

        ## jqplot
        ${h.stylesheet_link( app_root + "plugins/jqplot/jquery.jqplot.css" )}
        ${h.javascript_link( app_root + "plugins/jqplot/jquery.jqplot.js" )}
        ${h.javascript_link( app_root + "plugins/jqplot/jquery.jqplot.plugins.js" )}

        ## load merged/minified code
        ${h.javascript_link( app_root + "build-app.js" )}
        
        ## install default css
        ${h.stylesheet_link( app_root + "app.css" )}
    </head>

    <body>
        <script type="text/javascript">
            // get configuration
            var config = {
                root     : '${root}',
                app_root : '${app_root}'
            };
            
            // link galaxy
            var Galaxy = Galaxy || parent.Galaxy;

            // console protection
            window.console = window.console || {
                log     : function(){},
                debug   : function(){},
                info    : function(){},
                warn    : function(){},
                error   : function(){},
                assert  : function(){}
            };

            // configure require
            require.config({
                baseUrl: config.root + "static/scripts/",
                paths: {
                    "plugin"        : "${app_root}",
                    "d3"            : "libs/d3"
                },
                shim: {
                    "libs/underscore": { exports: "_" },
                    "libs/backbone/backbone": { exports: "Backbone" },
                    "d3": { exports: "d3"}

                }
            });

            // application
            var app = null;
            $(function() {   
                // request application script
                require(['plugin/app'], function(App) {
                    // load options
                    var options = {
                        id      : ${h.dumps( visualization_id )} || undefined,
                        config  : ${h.dumps( config )}
                    }
                    
                    // create application
                    app = new App(options);
                    
                    // add to body
                    $('body').append(app.$el);
                });
            });

        </script>
    </body>
</html>
