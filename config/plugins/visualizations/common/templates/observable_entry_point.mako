# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>

## Create a container, attach data and import script file
<%def name="get_body()">
    <%
        from markupsafe import escape

        ## Collect incoming data
        data_incoming = {
            "root": h.url_for("/"),
            "visualization_id": visualization_id,
            "visualization_name": visualization_name,
            "visualization_plugin": visualization_plugin,
            "visualization_title": escape(title),
            "visualization_config": config }

        ## Load script source
        script_src = script_attributes.get("src")
    %>

    ## Create container and initialize notebook
    <div id="app" data-incoming='${h.dumps(data_incoming)}'></div>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@observablehq/inspector@5/dist/inspector.css">
    <script type="module">
        import {Runtime, Inspector} from "https://cdn.jsdelivr.net/npm/@observablehq/runtime@5/dist/runtime.js";
        import define from "https://api.observablehq.com/d/${script_src}";
        new Runtime().module(define, Inspector.into("#app"));
    </script>
</%def>
