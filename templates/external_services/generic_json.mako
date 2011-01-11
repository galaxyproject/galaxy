<%inherit file="/base.mako"/>
<%namespace file="json_common.mako" import="display_item" />

<%def name="title()">Results from ${action.label} of ${param_dict['service_instance'].name} (${param_dict['service'].name}) on ${param_dict['item'].name}</%def>
    <div class="toolForm" id="json-result-${action.name}">
        <div class="toolFormTitle">Results from <i>${action.label}</i> of <i>${param_dict['service_instance'].name} (${param_dict['service'].name})</i> on <i>${param_dict['item'].name}</i></div>
        <div class="form-row">
            ${display_item( result )}
        </div>
    </div>

