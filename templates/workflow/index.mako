<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
    <title>Galaxy Workflows</title>
    <link rel="stylesheet" type="text/css" href="${h.url_for('/static/style/base.css')}"></link>
</head>
<body>
    <div class="warningmessage">
        Workflow support is currently in <b><i>beta</i></b> testing.
        Workflows may not work with all tools, may fail unexpectedly, and may
        not be compatible with future updates to <b>Galaxy</b>.
    </div>
    
    <h2>Workflow home</h2>
    
    <p>
        <a href="${h.url_for( action='editor')}" target="_parent">Create new workflow</a> using
        the <b>Galaxy</b> workflow editor
    </p>
    
    
    <h2>Stored workflows</h2>
    
    %if workflows:
        <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr class="header"><td>Name</td><td>Last Updated</td><td>Actions</td></tr>
            %for workflow in workflows:
                <tr>
                    <td>${workflow.name}</td>
                    <td>${str(workflow.update_time)[:19]}</td>
                    <td>
                        <a href="${h.url_for( action='run', workflow_name=workflow.name )}">run</a>
                        | <a href="${h.url_for( action='editor', workflow_name=workflow.name )}" target="_parent">edit</a>
                        | <a href="${h.url_for( action='delete', workflow_name=workflow.name )}">delete</a>
                </tr>    
            %endfor
        </table>
    %else:
    
        You have no stored workflows.
    
    %endif
    
</body>
</html>
