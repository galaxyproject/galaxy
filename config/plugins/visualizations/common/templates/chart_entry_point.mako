# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>
<%def name="stylesheets()">
    ${h.css('jquery-ui/smoothness/jquery-ui')}
    ${h.css('base')}
    <link rel="stylesheet" href="${script_attributes.get("css")}">
</%def>
<%def name="javascripts()">
    <script type="text/javascript">
        var Galaxy = Galaxy || parent.Galaxy || {
            root    : '${h.url_for( "/" )}',
            config  : {},
            emit    : {
                debug: function() {}
            }
        };
    </script>
    ${h.js('libs/jquery/jquery',
           'libs/jquery/jquery-ui',
           'libs/d3',
           'bundled/libs.bundled',
           'bundled/chart.bundled')}
    <script type="text/javascript" src="${script_attributes.get("src")}"></script>
    <script type="text/javascript">
        $(function() {
            var config = ${h.dumps(config)};
            var app = bundleEntries.chart({
                visualization_id: ${h.dumps(visualization_id)} || undefined,
                visualization_name: ${h.dumps(visualization_name)},
                visualization_plugin: ${h.dumps(visualization_plugin)},
                dataset_id: config.dataset_id,
                chart_dict: config.chart_dict,
                chart_func: bundleEntries["${script_attributes.get("func")}"]
            });
            $('body').append(app.$el);
        });
    </script>
</%def>