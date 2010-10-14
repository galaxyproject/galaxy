<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<% states_list = request_type.states %>

<h2>Sequencer Configuration "${request_type.name}"</h2>

<div class="toolForm">
    <div class="toolFormTitle">Sequencer configuration information</div>
    <form name="view_request_type" action="${h.url_for( controller='requests_admin', action='create_request_type', rt_id=trans.security.encode_id( request_type.id ))}" method="post" >
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
        <div class="toolFormTitle">Sequencer information</div>
        <div class="form-row">
            This information is only needed for transferring data from sequencer to Galaxy
        </div>
        <div class="form-row">
            <label>Hostname or IP Address:</label>
            <input type="text" name="host" value="${request_type.datatx_info['host']}" size="40"/>
        </div>
        <div class="form-row">
            <label>Username:</label>
            <input type="text" name="username" value="${request_type.datatx_info['username']}" size="40"/>
        </div>
        <div class="form-row">
            <label>Password:</label>
            <input type="password" name="password" value="${request_type.datatx_info['password']}" size="40"/>
        </div>
        <div class="form-row">
            <label>Data directory:</label>
            <input type="text" name="data_dir" value="${request_type.datatx_info.get('data_dir', '')}" size="40"/>
        </div>
        <div class="form-row">
            <label>Add experiment name and the sample name to the dataset name?</label>
            ${rename_dataset_select_field.get_html()}
            <div class="toolParamHelp" style="clear: both;">
                The datasets are renamed by prepending the experiment name and the sample name to the dataset name. <br/>This
                makes sure that dataset names remain unique in Galaxy even when they have the
                same name in the sequencer.
            </div>
        </div>
        <div class="form-row">
        <input type="submit" name="save_changes" value="Save changes"/>
        </div>
    </form>
</div>