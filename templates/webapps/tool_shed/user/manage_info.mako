<%inherit file="/base.mako"/>
<%namespace file="/user/info.mako" import="render_user_info" />
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

${render_user_info()}
