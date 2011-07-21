<%inherit file="/grid_base.mako"/>
<%namespace file="/requests/common/common.mako" import="common_javascripts" />
<%namespace file="/requests/common/common.mako" import="transfer_status_updater" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${common_javascripts()}
   ${transfer_status_updater()}
</%def>
