<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common.mako" import="render_available_templates" />

<% import os %>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%
    #should be able to associate roles with infos
    #roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
    #history = trans.get_history()
%>

${render_available_templates( library_item, library_id )}
