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
                'libs/jquery/jquery-ui',
                'libs/jquery/select2',
                'libs/bootstrap',
                'libs/underscore',
                'libs/backbone',
                'libs/d3',
                'libs/require')}

        ## shared css
        ${h.css( 'base', 'jquery-ui/smoothness/jquery-ui' )}

        ## crossfilter
        ${h.javascript_link( app_root + "plugins/crossfilter/crossfilter.js" )}

        ## canvg
        ${h.javascript_link( app_root + "plugins/canvg/rgbcolor.js" )}
        ${h.javascript_link( app_root + "plugins/canvg/canvg.js" )}

        ## biojs
        ${h.javascript_link( app_root + "plugins/biojs/biojs.msa.js" )}

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
            var app_root = '${app_root}';
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
                    "d3"            : "libs/d3"
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
                    var options = {
                        id      : ${h.dumps( visualization_id )} || undefined,
                        config  : ${h.dumps( config )}
                    }
                    var app = new App( options );
                    $( 'body' ).append( app.$el );
                });
            });
        </script>
    </body>
</html>
