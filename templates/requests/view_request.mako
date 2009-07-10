<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Request Details: '${request_details[0]['value']}'</div>
        %for index, rd in enumerate(request_details):
            <div class="form-row">
                <label>${rd['label']}</label>
                ##<i>${rd['helptext']}</i>                                   
                ${rd['value']}
            </div>
            <div style="clear: both"></div>
        %endfor
    </div>
</div>