<%inherit file="/base.mako"/>
<%namespace file="json_common.mako" import="display_item" />

<%def name="title()">${param_dict['service_instance'].name}: ${action.label}</%def>

<%def name="display_json_grid_result( headers, rows )">
    %for row in rows:
        %for name in headers:
            <div class="form-row">
                <label>${name}</label>
                ${display_item( row.get( name ) )}
                <div style="clear: both"></div>
            </div>
        %endfor
    %endfor
</%def>

<%
    #HACK!!!! need to use better method of displaying jqGrid here, needs to allow paging as optionally available.
    if 'Rows' in result: #paged
        records = result['Records']
        total = result['Total']
        rows = result['Rows']
        page = result['Page']
    else:
        rows = result
        records = None
        total = None
        page = None
    headers = rows[0].keys()
    if records:
        records_label = '<b>records:</b> %s' % str( records )
    else:
        records_label = ''
    if total:
        total_label = '<b>total:</b> %s' % str( total )
    else:
        total_label = ''
    if page:
        page_label = '<b>page:</b> %s' % str( page )
    else:
        page_label = ''
%>

<div class="toolForm">
    <div class="toolFormTitle">${action.label} of ${param_dict['service_instance'].name} (${param_dict['service'].name}) on ${param_dict['item'].name}</div>
    <div class="toolFormBody">
        %if records_label:
            ${records_label}
        %endif
        %if total_label:
            ${total_label}
        %endif
        %if page_label:
            ${page_label}
        %endif
        ${display_json_grid_result( headers, rows )}
    </div>
</div>
