<%inherit file="/base/base_panels.mako"/>

## Default title
<%def name="title()">Tool Shed</%def>

<%def name="init()">
    ${parent.init()}
    <%
        self.body_class = "toolshed"
    %>
</%def>

<%def name="javascript_app()">
    ${parent.javascript_app()}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

## Masthead
<%def name="masthead()">
</%def>
