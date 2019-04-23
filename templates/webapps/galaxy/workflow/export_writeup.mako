<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% _=n_ %>

<%def name="title()">Extract workflow from history</%def>

<%def name="stylesheets()">
    ${h.css( 'history', 'base' )}
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
                        <input type="hidden" id="as-input-${ encoded_id }" class="as-input"
                               name="${data.history_content_type}_ids" value="${data.hid}" checked="true" />
                        <label for="as-input-${ encoded_id }" ></label>
                        <input type="text" id="as-named-input-${ encoded_id }" class="as-named-input"
                               name="${data.history_content_type}_names" value="${data.display_name() | h}" />
                    %endif
                </div>
            </td>
        </tr>
    </table>
</%def>

<p>The following list contains each tool that was run to create the
datasets in your current history.</p>

<p>You have the option to change the workflow's name along with input data name if you so choose.
once ready create the writeup</p>


%for warning in warnings:
    <div class="warningmark">${warning}</div>
%endfor

<form method="post" action="${h.url_for(controller='workflow', action='export_writeup')}">
<div class='form-row'>
    <label>${_('Workflow name')}</label>
    <input name="workflow_name" type="text" value="${ util.unicodify( history.name )}" size="60"/>
</div>
<p>
    <input type="submit" value="${_('Create Write Up')}" />
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
        #cls += " toolFormDisabled"
        disabled = True
        tool_name = getattr( job, 'name', tool_name )
    else:
        tool = app.toolbox.get_tool( job.tool_id, tool_version=job.tool_version )
        if tool:
            tool_name = tool.name
        if tool is None or not( tool.is_workflow_compatible ):
            #cls += " toolFormDisabled"
            disabled = True
        else:
            disabled = False
        if tool and tool.version != job.tool_version:
            tool_version_warning = 'Dataset was created with tool version "%s", but workflow extraction will use version "%s".' % ( job.tool_version, tool.version )
        else:
            tool_version_warning = ''
    if disabled:
        disabled_why = getattr( job, 'disabled_why', "data" )
    %>

    <tr>
        <td>
            <div class="${cls}">

                <div class="toolFormTitle">${tool_name}</div>
                <div class="toolFormBody">
                    %if disabled:
                        <div>${disabled_why}</div>
                    %else:
                        <div><input type="hidden" name="job_ids" value="${job.id}" checked="true" />${tool_name}</div>
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
