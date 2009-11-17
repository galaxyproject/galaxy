<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Request type information</div>
    <form name="library">
        <div class="form-row">
            <label>Name</label>
            ${request_type.name}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Description</label>
            ${request_type.desc}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>
                Request Form definition 
            </label>
            ${request_type.request_form.name}
        </div>       
        <div class="form-row">
            <label>
                Sample Form definition 
            </label>
            ${request_type.sample_form.name}
        </div>    
        <div class="toolFormTitle">Possible sample states</div>
            %for element_count, state in enumerate(states_list):
                <div class="form-row">
                    <label>${1+element_count}. ${state.name}</label>
                    ${state.desc}
                </div>
                <div style="clear: both"></div>
            %endfor
    </form>
</div>