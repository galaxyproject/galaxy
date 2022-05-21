# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>
<%def name="stylesheets()">
    ${h.dist_css('base')}
    <%css_path = script_attributes.get("css") %>
    %if css_path is not None:
        <link rel="stylesheet" href="${static_url}${css_path}">
    %endif
</%def>
<%def name="javascripts()">
    ${h.dist_js(
           'libs.bundled',
           'generic.bundled')}
    <%src_path = script_attributes.get("src") %>
    <script type="text/javascript" src="${static_url}${src_path}"></script>
    <script type="text/javascript">
        config.addInitialization(function() {
            let dump = ${h.dumps(config)};
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
                    dataset_id: dump.dataset_id,
                    chart_dict: dump.chart_dict,
                    chart_load: bundleEntries[load]
                });
                $('body').css("overflow", "hidden")
                         .css("margin", 0)
                         .append(app.$el);
            }
        });
    </script>
</%def>
