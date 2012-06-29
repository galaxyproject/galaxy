<%inherit file="/grid_base.mako"/>
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${repository_installation_status_updater()}
   ${repository_installation_updater()}
</%def>
