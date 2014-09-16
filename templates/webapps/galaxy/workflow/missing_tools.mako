<%inherit file="/base.mako"/>

<h2>Cannot run workflow "${h.to_unicode( workflow.name )}"</h2>

%if workflow.annotation:
    <div class="workflow-annotation">${workflow.annotation}</div>
    <hr/>
%endif

<div class='errormessage'>
    <strong>This workflow utilizes tools which are unavailable, and cannot be run.  Enable the tools listed below, or <a href="${h.url_for(controller='workflow', action='editor', id=trans.security.encode_id(workflow.id) )}" target="_parent">edit the workflow</a> to correct these errors.</strong><br/>
    <ul>
    %for i, tool in enumerate( missing_tools ):
        <li>${tool}</li>
    %endfor
    </ul>
</div>