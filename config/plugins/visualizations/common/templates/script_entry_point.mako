# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>

## Add stylesheet
<%def name="stylesheets()">
    <% css = script_attributes.get("css") %>
    %if css is not None:
        <link rel="stylesheet" href="${css}">
    %endif
</%def>

## Create a container, attach data and import script file
<%def name="get_body()">
    ## Collect incoming data
    <%
        from markupsafe import escape
        data_incoming = {
            "root": h.url_for("/"),
            "visualization_id": visualization_id,
            "visualization_name": visualization_name,
            "visualization_plugin": visualization_plugin,
            "visualization_title": escape(title),
            "visualization_config": config }
    %>

    ## Create a container with default identifier `app`
    <% container = script_attributes.get("container") or "app" %>
    <div id="${container}" data-incoming='${h.dumps(data_incoming)}'></div>

    ## Add script tag
    <% script_src = script_attributes.get("src") %>
    <% script_type = script_attributes.get("type") or "module" %>
    <script type="${script_type}" src=${script_src}></script>
</%def>
