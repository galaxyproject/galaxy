<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<% import datetime %>
<%def name="title()">Display Application: ${display_link.link.display_application.name}  ${display_link.link.name}</%def>
%for message, status in msg:
    ${render_msg( message, status )}
%endfor

%if preparable_steps:
    <p>
        <h2>Preparation Status</h2>
        <table class="colored">
            <tr><th>Step Name</th><th>Ready</th><th>Dataset Status</th></tr>
            %for step_dict in preparable_steps:
                <tr><td>${ step_dict.get( "name" ) | h }</td><td>${ step_dict.get( "ready" ) | h }</td><td>${ step_dict.get( "value" ).state if step_dict.get( "value" ) else 'unknown' | h }</td></tr>
            %endfor
        </table>
    </p>
%endif


%if refresh:
<%def name="metas()"><meta http-equiv="refresh" content="3" /></%def>
<br /><br /><p>
This page will <a href="${trans.request.url}">refresh</a> after 3 seconds, and was last refreshed on ${ datetime.datetime.strftime( datetime.datetime.now(), "%Y-%m-%dT%H:%M:%S.Z" ) | h }.
</p>
%endif
