# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>
<%def name="stylesheets()">
    ${h.css('jquery-ui/smoothness/jquery-ui')}
    ${h.css('base')}
    <%css_path = script_attributes.get("css") %>
    %if css_path is not None:
        <link rel="stylesheet" href="${static_url}${css_path}">
    %endif
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
           'bundled/libs.bundled')}
    <%src_path = script_attributes.get("src") %>
    <script type="text/javascript" src="${static_url}${src_path}"></script>
    <script type="text/javascript">
        $(function() {
            var config = ${h.dumps(config)};
            var load = "${script_attributes.get("load")}";
            if (!bundleEntries[load]) {
                load = "load";
            }
            if (!bundleEntries[load]) {
                alert("Load function '" + load + "' not found.");
            } else {
                var app = bundleEntries.chart({
                    visualization_id: ${h.dumps(visualization_id)} || undefined,
                    visualization_name: ${h.dumps(visualization_name)},
                    visualization_plugin: ${h.dumps(visualization_plugin)},
                    dataset_id: config.dataset_id,
                    chart_dict: config.chart_dict,
                    chart_load: bundleEntries[load]
                });
                $('body').css("overflow", "hidden")
                         .css("margin", 0)
                         .append(app.$el);
            }
        });
    </script>
</%def>
