<%
    root        = h.url_for( "/" )
    app_root    = root + "plugins/visualizations/charts/static/"
    remote_root = app.config.get( "charts_plugins_url", "https://raw.githubusercontent.com/guerler/galaxy-charts/master/" )
%>

<!DOCTYPE HTML>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>${hda.name} | ${visualization_name}</title>

        ## install shared libraries
        ${h.js( 'libs/jquery/jquery',
                'libs/jquery/jquery-ui',
                'libs/jquery/select2',
                'libs/bootstrap',
                'libs/underscore',
                'libs/backbone',
                'libs/d3',
                'libs/require')}

        ## shared css
        ${h.css( 'base', 'jquery-ui/smoothness/jquery-ui' )}

        ## canvg
        ${h.javascript_link( app_root + "plugins/canvg/rgbcolor.js" )}
        ${h.javascript_link( app_root + "plugins/canvg/canvg.js" )}

        ## load merged/minified code
        ${h.javascript_link( app_root + "build-app.js" )}

        ## install default css
        ${h.stylesheet_link( app_root + "app.css" )}
    </head>

    <body>
        <script type="text/javascript">
            var app_root = '${app_root}';
            var remote_root = '${remote_root}';
            var Galaxy = Galaxy || parent.Galaxy || {
                root    : '${root}',
                emit    : {
                    debug: function() {}
                }
            };
            window.console = window.console || {
                log     : function(){},
                debug   : function(){},
                info    : function(){},
                warn    : function(){},
                error   : function(){},
                assert  : function(){}
            };
            require.config({
                baseUrl: Galaxy.root + "static/scripts/",
                paths: {
                    "plugin"        : "${app_root}",
                    "d3"            : "libs/d3",
                    "remote"        : "${remote_root}"
                },
                shim: {
                    "libs/underscore": { exports: "_" },
                    "libs/backbone": { exports: "Backbone" },
                    "d3": { exports: "d3"}

                }
            });
            window.onbeforeunload = function() {
                return 'You are leaving Charts.';
            };
            $(function() {
                require( [ 'plugin/app' ], function( App ) {
                    var app = new App({
                        id      : ${h.dumps( visualization_id )} || undefined,
                        config  : ${h.dumps( config )}
                    });
                    $( 'body' ).append( app.$el );
                });
            });
        </script>
    </body>
</html>