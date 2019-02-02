<%inherit file="/grid_base.mako"/>
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${dependency_status_updater()}
   ${tool_dependency_installation_updater()}
</%def>
