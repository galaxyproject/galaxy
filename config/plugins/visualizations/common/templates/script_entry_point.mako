# -*- coding: utf-8 -*-
<%inherit file="visualization_base.mako"/>

## No stylesheets
<%def name="stylesheets()"></%def>
## No javascript libraries
<%def name="late_javascripts()">
    <% tag_attrs = ' '.join([ '{0}="{1}"'.format( key, attr ) for key, attr in script_attributes.items() ]) %>
    <script type="text/javascript" ${tag_attrs}></script>
</%def>
