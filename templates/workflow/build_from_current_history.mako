<%inherit file="/base.mako"/>

<% _=n_ %>

<%def name="title()">Extract workflow from history</%def>

<%def name="stylesheets()">
    ${h.css( 'history', 'base' )}
    <style type="text/css">
    div.toolForm{
        margin-top: 10px;
        margin-bottom: 10px;
    }
    div.historyItem {
        margin-right: 0;
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
            return false;
        }).show();
        $("#uncheckall").click( function() {
            $("input[type=checkbox]").attr( 'checked', false );
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
    <div class="historyItemWrapper historyItem historyItem-${data_state}" id="historyItem-$data.id">
        <table cellpadding="0" cellspacing="0" border="0" width="100%">
            <tr>
                %if data_state != 'ok':
                    <td style="width: 20px;">
                        <div style='padding-right: 5px;'><img src="${h.url_for( str( '/static/style/data_%s.png' % data_state ) )}" border="0" align="middle"></div>
                    </td>
                %endif
                <td>
                    <div style="overflow: hidden;">
                        <span class="historyItemTitle"><b>${data.hid}: ${data.display_name()}</b></span>
                    </div>
                </td>
            </tr>
        </table>
        %if disabled:
            <hr>
            <div><input type="checkbox" name="dataset_ids" value="${data.hid}" checked="true" />${_('Treat as input dataset')}</div>
        %endif
    </div>
</%def>

<p>The following list contains each tool that was run to create the
datasets in your current history. Please select those that you wish
to include in the workflow.</p>

<p>Tools which cannot be run interactively and thus cannot be incorporated
into a workflow will be shown in gray.</p>

%for warning in warnings:
    <div class="warningmark">${warning}</div>
%endfor

<form method="post" action="${h.url_for()}">
<div class='form-row'>
    <label>${_('Workflow name')}</label>
    <input name="workflow_name" type="text" value="Workflow constructed from history '${history.name}'" size="60"/>
</div>
<p>
    <input type="submit" value="${_('Create Workflow')}" />
    <button id="checkall" style="display: none;">Check all</button>
    <button id="uncheckall" style="display: none;">Uncheck all</button>
</p>

<table border="0" cellspacing="0">
    
    <tr>
        <th style="width: 47.5%">${_('Tool')}</th>
        <th style="width: 5%"></th>
        <th style="width: 47.5%">${_('History items created')}</th>
    </tr>

%for job, datasets in jobs.iteritems():

    <%
    cls = "toolForm"
    tool_name = "Unknown"
    if hasattr( job, 'is_fake' ) and job.is_fake:
        cls += " toolFormDisabled"
        disabled = True
    else:    
        tool = app.toolbox.get_tool( job.tool_id )
        if tool:
            tool_name = tool.name
        if tool is None or not( tool.is_workflow_compatible ):
            cls += " toolFormDisabled"
            disabled = True
        else:
            disabled = False
    %>
    
    <tr>
        <td>
            <div class="${cls}">

                <div class="toolFormTitle">${tool_name}</div>
                <div class="toolFormBody">
                    %if disabled:
                        <div style="font-style: italic; color: gray">This tool cannot be used in workflows</div>
                    %else:
                        <div><input type="checkbox" name="job_ids" value="${job.id}" checked="true" />Include "${tool_name}" in workflow</div>
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