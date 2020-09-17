<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<% from galaxy.util import nice_size, unicodify %>

<style>
    .inherit {
        border: 1px solid #bbb;
        padding: 15px;
        text-align: center;
        background-color: #eee;
    }
</style>

<h2>
% if tool:
    ${tool.name | h}
% else:
    Unknown Tool
% endif
</h2>

<h3>Dataset Information</h3>
<table class="tabletip" id="dataset-details">
    <tbody>
        <%
        encoded_hda_id = trans.security.encode_id( hda.id )
        encoded_history_id = trans.security.encode_id( hda.history_id )
        %>
        <tr><td>Number:</td><td>${hda.hid | h}</td></tr>
        <tr><td>Name:</td><td>${hda.name | h}</td></tr>
        <tr><td>Created:</td><td>${unicodify(hda.create_time.strftime(trans.app.config.pretty_datetime_format))}</td></tr>
        ##      <tr><td>Copied from another history?</td><td>${hda.source_library_dataset}</td></tr>
        <tr><td>Filesize:</td><td>${nice_size(hda.dataset.file_size)}</td></tr>
        <tr><td>Dbkey:</td><td>${hda.dbkey | h}</td></tr>
        <tr><td>Format:</td><td>${hda.ext | h}</td></tr>
    </tbody>
</table>

<h3>Job Information</h3>
<table class="tabletip">
    <tbody>
        %if job:
            <tr><td>Galaxy Tool ID:</td><td>${ job.tool_id | h }</td></tr>
            <tr><td>Galaxy Tool Version:</td><td>${ job.tool_version | h }</td></tr>
        %endif
        <tr><td>Tool Version:</td><td>${hda.tool_version | h}</td></tr>
        <tr><td>Tool Standard Output:</td><td><a href="${h.url_for( controller='dataset', action='stdout', dataset_id=encoded_hda_id )}">stdout</a></td></tr>
        <tr><td>Tool Standard Error:</td><td><a href="${h.url_for( controller='dataset', action='stderr', dataset_id=encoded_hda_id )}">stderr</a></td></tr>
        %if job:
            <tr><td>Tool Exit Code:</td><td>${ job.exit_code | h }</td></tr>
            %if job.job_messages:
            <tr><td>Job Messages</td><td><ul style="padding-left: 15px; margin-bottom: 0px">
            %for job_message in job.job_messages:
            <li>${ job_message['desc'] |h }</li>
            %endfor
            <ul></td></tr>
            %endif
        %endif
        <tr><td>History Content API ID:</td>
        <td>${encoded_hda_id}
            %if trans.user_is_admin:
                (${hda.id})
            %endif
        </td></tr>
        %if job:
            <tr><td>Job API ID:</td>
            <td>${trans.security.encode_id( job.id )}
                %if trans.user_is_admin:
                    (${job.id})
                %endif
            </td></tr>
            %if job.copied_from_job_id:
            <tr><td>Copied from Job API ID:</td>
            <td>${trans.security.encode_id( job.copied_from_job_id )}
                %if trans.user_is_admin:
                    (${job.copied_from_job_id})
                %endif
            </td></tr>
            %endif
        %endif
        <tr><td>History API ID:</td>
        <td>${encoded_history_id}
            %if trans.user_is_admin:
                (${hda.history_id})
            %endif
        </td></tr>
        %if hda.dataset.uuid:
        <tr><td>UUID:</td><td>${hda.dataset.uuid}</td></tr>
        %endif
        %if trans.user_is_admin or trans.app.config.expose_dataset_path:
            %if not hda.purged:
                <tr><td>Full Path:</td><td>${hda.file_name | h}</td></tr>
            %endif
        %endif
    </tbody>
</table>

%if job:
<div class="job-parameters" dataset_id="${encoded_hda_id}" dataset_type="hda">
</div>
%endif



<h3>Inheritance Chain</h3>
<div class="inherit" style="background-color: #fff; font-weight:bold;">${hda.name | h}</div>

% for dep in inherit_chain:
    <div style="font-size: 36px; text-align: center; position: relative; top: 3px">&uarr;</div>
    <div class="inherit">
        '${dep[0].name | h}' in ${dep[1]}<br/>
    </div>
% endfor



%if job and job.command_line and (trans.user_is_admin or trans.app.config.expose_dataset_path):
<h3>Command Line</h3>
<pre class="code">
${ job.command_line | h }</pre>
%endif

%if job and (trans.user_is_admin or trans.app.config.expose_potentially_sensitive_job_metrics):
<div class="job-metrics" dataset_id="${encoded_hda_id}" aws_estimate="${trans.app.config.aws_estimate}" dataset_type="hda">
</div>
%endif

%if trans.user_is_admin:
<h3>Destination Parameters</h3>
<div class="job-destination-parameters" job_id="${trans.security.encode_id(job.id)}">
</div>
%endif

%if job and job.dependencies:
<h3>Job Dependencies</h3>
    <table class="tabletip">
        <thead>
        <tr>
            <th>Dependency</th>
            <th>Dependency Type</th>
            <th>Version</th>
            %if trans.user_is_admin:
            <th>Path</th>
            %endif
        </tr>
        </thead>
        <tbody>

            %for dependency in job.dependencies:
                <tr><td>${ dependency['name'] | h }</td>
                    <td>${ dependency['dependency_type'] | h }</td>
                    <td>${ dependency['version'] | h }</td>
                    %if trans.user_is_admin:
                        %if 'environment_path' in dependency:
                        <td>${ dependency['environment_path'] | h }</td>
                        %elif 'path' in dependency:
                        <td>${ dependency['path'] | h }</td>
                        %else:
                        <td></td>
                        %endif
                    %endif
                </tr>
            %endfor

        </tbody>
    </table>
%endif

%if hda.peek:
    <h3>Dataset peek</h3>
    <pre class="dataset-peek">${hda.peek}
    </pre>
%endif


<script type="text/javascript">
$(function(){
    $( '.input-dataset-show-params' ).on( 'click', function( ev ){
        ## some acrobatics to get the Galaxy object that has a history from the contained frame
        if( window.parent.Galaxy && window.parent.Galaxy.currHistoryPanel ){
            window.parent.Galaxy.currHistoryPanel.scrollToId( 'dataset-' + $( this ).data( 'hda-id' ) );
        }
    })
    window.bundleEntries.mountJobMetrics();
    window.bundleEntries.mountJobParameters();
    window.bundleEntries.mountDestinationParams();
});
</script>
