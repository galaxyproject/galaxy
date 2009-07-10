<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Sample Details: '${sample_details[0]['value']}'</div>
       %for index, rd in enumerate(sample_details):
            <div class="form-row">
                <label>${rd['label']}</label>            
                ${rd['value']}
            </div>
            <div style="clear: both"></div>
       %endfor
    </div>
</div>
