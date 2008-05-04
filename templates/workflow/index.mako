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
    
    %if message:
    <%
        try:
            messagetype
        except:
            messagetype = "done"
    %>
    <p/>
    <div class="${messagetype}message">
        ${message}
    </div>
    %endif
    
    <h2>Workflow home</h2>
    
    <div class="toolForm">
        <div class="toolFormTitle">Create new workflow</div>
            <div class="toolFormBody">
                <form action="${h.url_for( action='create' )}" method="POST">
                    <div class="form-row">
                        <label>
                            Name for new workflow
                        </label>
                        <div style="float: left; width: 250px; margin-right: 10px;">
                            <input type="text" name="workflow_name" value="Unnamed workflow" size="40">
                        </div>
                        <div style="clear: both"></div>
                    </div>
                    <div class="form-row">
                        <input type="submit" value="Create"></input>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <h2>Stored workflows</h2>

    %if workflows:
        <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
            <tr class="header"><td>Name</td><td># of Steps<td>Last Updated</td><td>Actions</td></tr>
            %for workflow in workflows:
                <tr>
                    <td>${workflow.name}</td>
                    <td>${len(workflow.latest_workflow.steps)}
                    <td>${str(workflow.update_time)[:19]}</td>
                    <td>
                        <a href="${h.url_for( action='run', id=trans.security.encode_id(workflow.id) )}">run</a>
                        | <a href="${h.url_for( action='editor', id=trans.security.encode_id(workflow.id) )}" target="_parent">edit</a>
                        | <a href="${h.url_for( action='delete', id=trans.security.encode_id(workflow.id) )}">delete</a>
                </tr>    
            %endfor
        </table>
    %else:
    
        You have no stored workflows.
    
    %endif
    
</body>
</html>
