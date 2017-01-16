<%
    root            = h.url_for( "/" )
    app_root        = root + "plugins/visualizations/charts/static/client"
    repository_root = root + "plugins/visualizations/charts/static/repository"
%>

<!DOCTYPE HTML>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>${hda.name | h} | ${visualization_name}</title>
        ${h.js( 'libs/jquery/jquery',
                'libs/jquery/jquery-ui',
                'libs/jquery/select2',
                'libs/bootstrap',
                'libs/underscore',
                'libs/backbone',
                'libs/d3',
                'libs/require')}
        ${h.css( 'base', 'jquery-ui/smoothness/jquery-ui' )}
        ${h.stylesheet_link( app_root + "/app.css" )}
    </head>
    <body>
        <script type="text/javascript">
            var app_root = '${app_root}';
            var repository_root = '${repository_root}';
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
                    "repository"    : "${repository_root}"
                },
                shim: {
                    "libs/underscore": { exports: "_" },
                    "libs/backbone": { exports: "Backbone" },
                    "d3": { exports: "d3" }
                }
            });
            $(function() {
                require( [ 'plugin/app' ], function( App ) {
                    var config = ${ h.dumps( config ) };
                    var app = new App({
                        visualization_id : ${ h.dumps( visualization_id ) } || undefined,
                        dataset_id       : config.dataset_id,
                        chart_dict       : config.chart_dict
                    });
                    $( 'body' ).append( app.$el );
                });
            });
        </script>
    </body>
</html>