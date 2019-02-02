<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Data Manager: ${ data_manager.name | h } - ${ data_manager.description | h }</%def>

%if message:
    ${render_msg( message, status )}
%endif

<h2>Data Manager: ${ data_manager.name | h } - ${ data_manager.description | h }</h2>

%if view_only:
    <p>Not implemented</p>
%else:
    <p>Access managed data by job</p>
    
%if jobs:
<div>
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <td>Actions</td>
            <td>Job ID</td>
            <td>User</td>
            <td>Last Update</td>
            <td>State</td>
            <td>Command Line</td>
            <td>Job Runner</td>
            <td>PID/Cluster ID</td>
        </tr>
        %for job in jobs:
                <td>
                    <div class="icon-btn-group">
                        <a class="icon-btn" href="${ h.url_for( controller="data_manager", action="view_job", id=trans.security.encode_id( job.id ) ) }" title="View info"><span class="fa fa-info-circle"></span></a><a class="icon-btn" href="${ h.url_for( controller="tool_runner", action="rerun", job_id=trans.security.encode_id( job.id ) ) }" title="Rerun"><span class="fa fa-refresh"></span></a>
                    </div>
                </td>
                <td>${ job.id | h }</td>
                %if job.history and job.history.user:
                    <td>${job.history.user.email | h}</td>
                %else:
                    <td>anonymous</td>
                %endif
                <td>${job.update_time | h}</td>
                <td>${job.state | h}</td>
                <td>${job.command_line | h}</td>
                <td>${job.job_runner_name | h}</td>
                <td>${job.job_runner_external_id | h}</td>
            </tr>
        %endfor
    </table>
    <p/>
</div>
%else:
    <div class="infomessage">There are no jobs for this data manager.</div>
%endif

%endif
