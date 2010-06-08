<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="toolForm">
    <div class="toolFormBody">
        <h3 align="center">Job Information</h3>
        <table align="center" class="colored">
            <tr class="header">
                <td>State</td>
                <td>Job Id</td>
                <td>Create Time</td>
                <td>Update Time</td>
                <td>Session Id</td>
            </tr>
            <tr>
                <td>${job_info.state}</td>
                <td>${job_id}</td>
                <td>${job_info.create_time}</td>
                <td>${job_info.update_time}</td>
                <td>${job_info.session_id}</td>
            </tr>
                <tr class="header">
                <td colspan="3">Tool</td>
                <td colspan="2">User</td>
            </tr>
            <tr>
                <td colspan="3">${job_info.tool_id}</td>
                <td colspan="2">
                    %if job_info.email:
                        ${job_info.email}
                    %else:
                        anonymous
                    %endif
                </td>
            </tr>
            <tr class="header">
                <td colspan="5">Remote Host</td>
            </tr>
            <tr>
                <td colspan="5">${job_info.remote_host}</td>
            </tr>
            <tr class="header">
                <td colspan="5">Command Line</td>
            </tr>
            <tr>
                <td colspan="5">${job_info.command_line}</td>
            </tr>
            <tr class="header">
                <td colspan="5">Stderr</td>
            </tr>
            <tr>
                <td colspan="5"><pre>${job_info.stderr}</pre></td>
            </tr>
            <tr class="header">
                <td colspan="5">Stack Trace</td>
            </tr>
            <tr>
                <td colspan="5"><pre>${job_info.traceback}</pre></td>
            </tr>
            <tr class="header">
                <td colspan="5">Info</td>
            </tr>
            <tr>
                <td colspan="5">${job_info.info}</td>
            </tr>
            <tr><td colspan="5">&nbsp;</td></tr>
            <tr><td colspan="5">&nbsp;</td></tr>
        </table>
    </div>
</div>
