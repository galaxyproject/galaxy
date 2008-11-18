<%inherit file="/base.mako"/>
<%def name="title()">Change Default Permissions on New Histories</%def>
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />

%if trans.user:
    ${render_permission_form( trans.user, trans.user.email, h.url_for(), 'id', None, trans.user.all_roles() )}
%endif
