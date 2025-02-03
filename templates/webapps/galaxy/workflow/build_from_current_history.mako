<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% _=n_ %>

<%def name="title()">Extract workflow from history</%def>

<%def name="stylesheets()">
    ${h.dist_css( 'base' )}
    ${h.css( 'history' )}
    <style type="text/css">
    div.toolForm{
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .list-item.dataset.history-content {
        padding: 8px 10px;
    }
    .list-item.dataset.history-content .title-bar {
        cursor: auto;
    }
    input[type="checkbox"].as-input {
        margin-left: 8px;
    }
    th {
        border-bottom: solid black 1px;
    }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
    $(function() {
        $("#checkall").click( function() {
            $("input[type=checkbox]").attr( 'checked', true );
            $(".as-named-input").prop( 'disabled', false );
            return false;
        }).show();
        $("#uncheckall").click( function() {
            $("input[type=checkbox]").attr( 'checked', false );
            $(".as-named-input").prop( 'disabled', true );
            return false;
        }).show();
    });
    </script>
</%def>

<%def name="history_item( data, creator_disabled=False )">
    %if data.state in [ "no state", "", None ]:
        <% data_state = "queued" %>
    %else:
        <% data_state = data.state %>
    %endif
    <% encoded_id = trans.app.security.encode_id( data.id ) %>
    <table cellpadding="0" cellspacing="0" border="0" width="100%">
        <tr>
            <td>
                <div class="list-item dataset history-content state-${ data.state }" id="dataset-${ encoded_id }">
                    <div class="title-bar clear">
                        <div class="title">
                            <span class="hid">${data.hid}</span>
                            <span class="name">${data.display_name()}</span>
                        </div>
                    </div>
                    %if disabled:
                        <input type="checkbox" id="as-input-${ encoded_id }" class="as-input"
                               name="${data.history_content_type}_ids" value="${data.hid}" checked="true"
                               onclick="document.getElementById('as-named-input-${ encoded_id }').disabled = !document.getElementById('as-input-${ encoded_id }').checked" />
                        <label for="as-input-${ encoded_id }" >Treat as input dataset</label>
                        <input type="text" id="as-named-input-${ encoded_id }" class="as-named-input"
                               name="${data.history_content_type}_names" value="${data.display_name() | h}" />
                    %endif
                </div>
            </td>
        </tr>
    </table>
</%def>

<p>The following list contains each tool that was run to create the
datasets in your current history. Please select those that you wish
to include in the workflow.</p>

<p>Tools which cannot be run interactively and thus cannot be incorporated
into a workflow will be shown in gray.</p>

%for warning in warnings:
    <div class="warningmark">${warning}</div>
%endfor

<form method="post" action="${h.url_for(controller='workflow', action='build_from_current_history', history_id=trans.security.encode_id(history.id))}">
<div class='form-row'>
    <label>Workflow name</label>
    <input name="workflow_name" type="text" value="Workflow constructed from history '${ util.unicodify( history.name )}'" size="60"/>
</div>
<p>
    <input type="submit" class="btn btn-primary" value="Create Workflow" />
    <button id="checkall" style="display: none;">Check all</button>
    <button id="uncheckall" style="display: none;">Uncheck all</button>
</p>

<table border="0" cellspacing="0">

    <tr>
        <th style="width: 47.5%">Tool</th>
        <th style="width: 5%"></th>
        <th style="width: 47.5%">History items created</th>
    </tr>

%for job, datasets in jobs.items():

    <%
    cls = "toolForm"
    tool_name = "Unknown"
    if hasattr( job, 'is_fake' ) and job.is_fake:
        cls += " toolFormDisabled"
        disabled = True
        tool_name = getattr( job, 'name', tool_name )
    else:
        tool = app.toolbox.get_tool( job.tool_id, tool_version=job.tool_version )
        if tool:
            tool_name = tool.name
        if tool is None or not( tool.is_workflow_compatible ):
            cls += " toolFormDisabled"
            disabled = True
        else:
            disabled = False
        if tool and tool.version != job.tool_version:
            tool_version_warning = 'Dataset was created with tool version "%s", but workflow extraction will use version "%s".' % ( job.tool_version, tool.version )
        else:
            tool_version_warning = ''
    if disabled:
        disabled_why = getattr( job, 'disabled_why', "This tool cannot be used in workflows" )
    %>

    <tr>
        <td>
            <div class="${cls}">

                <div class="toolFormTitle">${tool_name}</div>
                <div class="toolFormBody">
                    %if disabled:
                        <div style="font-style: italic; color: gray">${disabled_why}</div>
                    %else:
                        <div><input type="checkbox" name="job_ids" value="${job.id}" checked="true" />Include "${tool_name}" in workflow</div>
                        %if tool_version_warning:
                            ${ render_msg( tool_version_warning, status="warning" ) }
                        %endif
                    %endif
                </div>
            </div>
        </td>
        <td style="text-align: center;">
            &#x25B6;
        </td>
        <td>
            %for _, data in datasets:
                <div>${history_item( data, disabled )}</div>
            %endfor
        </td>
    </tr>

%endfor

</table>

</form>
