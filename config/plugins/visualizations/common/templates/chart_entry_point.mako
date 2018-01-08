# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>
<%
    root            = h.url_for( "/" )
    app_root        = root + "plugins/visualizations/charts/static/client"
    repository_root = root + "plugins/visualizations/charts/static/repository"
%>

## Default stylesheets
<%def name="stylesheets()">
    ${h.css('base')}
</%def>

## No javascript libraries
<%def name="late_javascripts()">
    <% tag_attrs = ' '.join([ '{0}="{1}"'.format( key, attr ) for key, attr in script_tag_attributes.items() ]) %>
    <script type="text/javascript">
        ## global configuration object
        var Galaxy = Galaxy || parent.Galaxy || {
            root    : '${h.url_for( "/" )}',
            config  : {},
            emit    : {
                debug: function() {}
            }
        };
    </script>
    ${h.js('libs/require',
           'bundled/libs.bundled',
           'bundled/chart.bundled')}
    <script type="text/javascript">
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
            urlArgs: 'v=${app.server_starttime}'
        });
        $(function() {
            var config = ${ h.dumps( config ) };
            var app = bundleEntries.chart({
                visualization_id    : ${h.dumps(visualization_id)} || undefined,
                visualization_name  : ${h.dumps(visualization_name)},
                visualization_plugin: ${h.dumps(visualization_plugin)},
                dataset_id          : config.dataset_id,
                chart_dict          : config.chart_dict
            });
            $('body').append(app.$el);
        });
    </script>
</%def>