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

<%
encoded_hda_id = trans.security.encode_id( hda.id )
encoded_history_id = trans.security.encode_id( hda.history_id )
%>

<div class="dataset-information" hda_id="${encoded_hda_id}"></div>
<p>
%if job:
<div class="job-parameters" dataset_id="${encoded_hda_id}" dataset_type="hda">
</div>
<p>
%endif
<div class="job-information" hda_id="${encoded_hda_id}" job_id="${trans.security.encode_id( job.id )}"></div>
<p>
<div class="dataset-storage" dataset_id="${encoded_hda_id}" dataset_type="hda"></div>
<p>

<h3>Inheritance Chain</h3>
<div class="inherit" style="background-color: #fff; font-weight:bold;">${hda.name | h}</div>

% for dep in inherit_chain:
    <div style="font-size: 36px; text-align: center; position: relative; top: 3px">&uarr;</div>
    <div class="inherit">
        '${dep[0].name | h}' in ${dep[1]}<br/>
    </div>
% endfor
<p>

%if job and (trans.user_is_admin or trans.app.config.expose_potentially_sensitive_job_metrics):
<div class="job-metrics" dataset_id="${encoded_hda_id}" aws_estimate="${trans.app.config.aws_estimate}" dataset_type="hda">
</div>
<p>
%endif

%if trans.user_is_admin:
<h3>Destination Parameters</h3>
<div class="job-destination-parameters" job_id="${trans.security.encode_id(job.id)}">
</div>
<p>
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
    <p>
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

     const mountComponents = ["mountJobMetrics", "mountJobParameters", "mountDestinationParams","mountDatasetInformation","mountJobInformation", "mountDatasetStorage"]
     mountComponents.forEach(component => window.bundleEntries[component]())
});
</script>
