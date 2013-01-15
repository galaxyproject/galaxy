
<%inherit file="/webapps/galaxy/base_panels.mako"/>
<%namespace file="/search/search.mako" import="search_init" />
<%namespace file="/search/search.mako" import="search_dialog" />

<%def name="init()">
<%
    self.has_left_panel = False
    self.has_right_panel = False
    self.active_view = "profile"
%>
</%def>

<%def name="center_panel()">

${search_init()}

${search_dialog()}

</%def>

