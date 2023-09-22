<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% import datetime %>

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
    <div class="reportBody">
        <h3 align="center">Job Information</h3>
        <table align="center" class="colored">
            <tr class="header">
                <td>State</td>
                <td>Job Id</td>
                <td>Create Time</td>
                <td>Time To Finish</td>
                <td>Session Id</td>
            </tr>
            <tr>
                <td><div class="count-box state-color-${job.state}">${job.state}</div></td>
                <td>${job.id}</td>
                <td>${job.create_time}</td>
                <td>
                    <% execute_time = job.update_time - job.create_time %>
                    ${datetime.timedelta( seconds=execute_time.seconds )}
                </td>
                <td>${job.session_id}</td>
            </tr>
                <tr class="header">
                <td colspan="2">Tool</td>
                <td>User</td>
                <td>Runner</td>
                <td>Runner Id</td>
            </tr>
            <tr>
                <td colspan="2">${job.tool_id}</td>
                <td>
                    %if job.get_user_email():
                        ${job.get_user_email()}
                    %else:
                        anonymous
                    %endif
                </td>
                <td>${job.job_runner_name}</td>
                <td>${job.job_runner_external_id}</td>
            </tr>
            <tr class="header">
                <td colspan="3">Remote Host</td>
                <td>Destination Id</td>
                <td>Destination params</td>
            </tr>
            <tr>
                <td colspan="3">
                    %if job.galaxy_session and job.galaxy_session.remote_host:
                        ${job.galaxy_session.remote_host}
                    %else:
                        no remote host
                    %endif
                </td>
                <td>${job.destination_id}</td>
                <td>${job.destination_params}</td>
            </tr>
            <tr class="header">
                <td colspan="5">Command Line</td>
            </tr>
            <tr>
                <td colspan="5">${job.command_line}</td>
            </tr>
            <tr class="header">
                <td colspan="5">Stdout</td>
            </tr>
            <tr>
                <td colspan="5"><pre>${job.stdout}</pre></td>
            </tr>
            <tr class="header">
                <td colspan="5">Stderr</td>
            </tr>
            <tr>
                <td colspan="5"><pre>${job.stderr}</pre></td>
            </tr>
            <tr class="header">
                <td colspan="5">Stack Trace</td>
            </tr>
            <tr>
                <td colspan="5"><pre>${job.traceback}</pre></td>
            </tr>
            <tr class="header">
                <td colspan="5">Info</td>
            </tr>
            <tr>
                <td colspan="5">${job.info}</td>
            </tr>
            <tr><td colspan="5">&nbsp;</td></tr>
            <tr><td colspan="5">&nbsp;</td></tr>
        </table>
    </div>
</div>

