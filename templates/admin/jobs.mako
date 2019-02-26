<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        function toggle_all(source) {
            // sets all checkboxes in source's parent form to match source element.
            $.each($(source).closest("form").find(":checkbox"), function(i, v){
                v.checked = source.checked;
            });
        }
    </script>
</%def>

<%def name="title()">Jobs</%def>

<h2>Jobs</h2>

%if message:
    ${render_msg( message, status )}
%endif

<p>
    Unfinished and recently finished jobs are displayed on this page.  The
    'cutoff' input box will do two things -- it will limit the display of
    unfinished jobs to only those jobs that have not had their job state
    updated recently, and it will limit the recently finished jobs list to only
    displaying jobs that have finished since the cutoff.
</p>
<p>
    If any jobs are displayed, you may choose to stop them.  Your stop message
    will be displayed to the user as: "This job was stopped by an
    administrator: <b>&lt;YOUR MESSAGE&gt;</b>  For more information or help,
    report this error".
</p>

%if jobs:
<form name="jobs" action="${h.url_for(controller='admin', action='jobs')}" method="POST">
    <h4>
        Unfinished Jobs: These jobs are unfinished and have had their state updated in the previous ${cutoff} seconds.
    </h4>
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <td><input type="checkbox" onClick="toggle_all(this)"/></td>
            <td>Job ID</td>
            <td>User</td>
            <td>Last Update</td>
            <td>Tool</td>
            <td>State</td>
            <td>Inputs</td>
            <td>Command Line</td>
            <td>Job Runner</td>
            <td>PID/Cluster ID</td>
        </tr>
        %for job in jobs:
                <td>
                    <input type="checkbox" name="stop" value="${job.id}"/>
                </td>
                <td>${job.id}</td>
                %if job.history and job.history.user:
                    <td>${job.history.user.email|h}</td>
                %else:
                    <td>anonymous</td>
                %endif
                <td>${last_updated[job.id]} ago</td>
                <td>${job.tool_id|h}</td>
                <td>${job.state}</td>
                <%
                    try:
                        inputs = ", ".join( [ '%s&nbsp;%s' % ( da.dataset.id, da.dataset.state ) for da in job.input_datasets ] )
                    except:
                        inputs = 'Unable to determine inputs'
                %>
                <td>${inputs}</td>
                <td>${job.command_line|h}</td>
                <td>${job.job_runner_name|h}</td>
                <td>${job.job_runner_external_id}</td>
            </tr>
        %endfor
    </table>
    <p/>
    <div class="card">
        <div class="card-header">
            Stop Jobs
        </div>
        <div class="card-body">
            <div class="form-row">
                <label>
                    Stop message:
                </label>
                <div class="form-row-input">
                    <input type="text" name="stop_msg" size="40"/>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    to be displayed to the user
                </div>
            </div>
            <div class="form-row">
                <input type="submit" class="primary-button" name="submit" value="Submit">
            </div>
        </div>
    </div>
    <p/>
</form>
%else:
    <div class="infomessage">There are no unfinished jobs to show with current cutoff time.</div>
    <p/>
%endif

%if recent_jobs:
    <h4>
        Recent Jobs: These jobs have completed in the previous ${cutoff} seconds.
    </h4>
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <td>Job ID</td>
            <td>User</td>
            <td>Finished</td>
            <td>Tool</td>
            <td>State</td>
            <td>Inputs</td>
            <td>Command Line</td>
            <td>Job Runner</td>
            <td>PID/Cluster ID</td>
        </tr>
        %for job in recent_jobs:
                <td><a href="${h.url_for( controller="admin", action="job_info" )}?jobid=${job.id}">${job.id}</a></td>
                %if job.history and job.history.user:
                    <td>${job.history.user.email|h}</td>
                %else:
                    <td>anonymous</td>
                %endif
                <td>${finished[job.id]} ago</td>
                <td>${job.tool_id|h}</td>
                <td>${job.state}</td>
                <%
                    try:
                        inputs = ", ".join( [ '%s&nbsp;%s' % ( da.dataset.id, da.dataset.state ) for da in job.input_datasets ] )
                    except:
                        inputs = 'Unable to determine inputs'
                %>
                <td>${inputs}</td>
                <td>${job.command_line|h}</td>
                <td>${job.job_runner_name|h}</td>
                <td>${job.job_runner_external_id|h}</td>
            </tr>
        %endfor
    </table>
    <p/>
%else:
    <div class="infomessage">There are no recently finished jobs to show with current cutoff time.</div>
    <p/>
%endif

<form name="jobs" action="${h.url_for(controller='admin', action='jobs')}" method="POST">
    <div class="card">
        <div class="card-header">
            Update Jobs
        </div>
        <div class="card-body">

            <div class="form-row">
                <label>
                    Cutoff:
                </label>
                <div class="form-row-input">
                    <input type="text" name="cutoff" size="4" value="${cutoff}"/>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    In seconds
                </div>
            </div>
            <div class="form-row">
                <input type="submit" class="primary-button" name="submit" value="Refresh">
            </div>
        </div>
    </div>
</form>

<form name="jobs" action="${h.url_for(controller='admin', action='jobs')}" method="POST">
    <p/>
    <div class="card">
        <div class="card-header">
            Administrative Job Lock
        </div>
        <div class="card-body">
            <div class="form-row">
                <input type="hidden" name="ajl_submit" value="True"/>
    %if job_lock==True:
                <p>Job dispatching is currently <strong>locked</strong>.</p>
                <label>
                    <input type='checkbox' name='job_lock' checked='checked' />
                    Prevent jobs from dispatching.
                </label>
    %else:
                <p>Job dispatching is currently <strong>unlocked</strong>.</p>
                <label>
                    <input type='checkbox' name='job_lock' />
                    Prevent jobs from dispatching.
                </label>
    %endif
            </div>
            <div class="form-row">
                <input type="submit" class="primary-button" name="submit" value="Update">
            </div>
        </div>
    </div>
</form>
