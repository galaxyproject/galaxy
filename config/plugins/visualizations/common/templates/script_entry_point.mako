# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>

## No stylesheets
<%def name="stylesheets()"></%def>

## Create a container, attach data and import script file
<%def name="late_javascripts()">
    <% container = script_attributes.get("container") or "app" %>
    <% data_incoming = {
        "visualization_id": visualization_id,
        "visualization_name": visualization_name,
        "visualization_plugin": visualization_plugin,
        "visualization_config": config }
    %>
    <div id="${container}" data-incoming='${h.dumps(data_incoming)}'></div>
    <% tag_attrs = ' '.join([ '{0}="{1}"'.format( key, attr ) for key, attr in script_attributes.items() ]) %>
    <script type="text/javascript" ${tag_attrs}></script>
</%def>
