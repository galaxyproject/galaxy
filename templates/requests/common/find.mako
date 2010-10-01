<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<%def name="javascripts()">
   ${parent.javascripts()}
   ${h.js("jquery.autocomplete", "autocomplete_tagging" )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>

<br/>
<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller=cntrller, cntrller=cntrller, action='list')}">
        <span>Browse requests</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Find samples</div>
    <div class="toolFormBody">
        <form name="find_request" id="find_request" action="${h.url_for( controller='requests_common', action='find', cntrller=cntrller)}" method="post" >
            <div class="form-row">
                <label>Find sample(s) using:</label>
                ${search_type.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Select a sample attribute to search through all the samples.<br/>
                    To search for a sample with a dataset name, select the dataset 
                    option above. This will return all the sample(s) which has a 
                    dataset with the given name associated with it. 
                </div>
            </div>
            <div class="form-row">
                <label>Show only sequencing requests in state:</label>
                ${request_states.get_html()}
            </div>
            <div class="form-row">
                ${search_box.get_html()}
                <input type="submit" name="go_button" value="Find"/>  
                <div class="toolParamHelp" style="clear: both;">
                   Wildcard search (%) can be used as placeholder for any sequence of characters or words.<br/> 
                   For example, to search for samples starting with 'mysample' use 'mysample%' as the search string.
                </div>
            </div>
            %if results:
	            <div class="form-row">
                    <label><i>${results}</i></label>
                    %if samples:
		                <div class="toolParamHelp" style="clear: both;">
		                   The search results are sorted by the date the samples where created. 
		                </div>
	                %endif
	            </div>
	        %endif
            <div class="form-row">
	            %if samples:
	                %for s in samples:
	                    <div class="form-row">
                            Sample: <b>${s.name}</b> | Barcode: ${s.bar_code}<br/>
                            State: ${s.current_state().name}<br/>
                            Datasets: <a href="${h.url_for(controller='requests_common', cntrller=cntrller, action='show_datatx_page', sample_id=trans.security.encode_id(s.id))}">${s.transferred_dataset_files()}/${len(s.datasets)}</a><br/>
                            %if cntrller == 'requests_admin':
                               <i>User: ${s.request.user.email}</i>
                            %endif
                            <div class="toolParamHelp" style="clear: both;">
                            <a href="${h.url_for( controller=cntrller, action='list', operation='show', id=trans.security.encode_id(s.request.id))}">Sequencing request: ${s.request.name} | Type: ${s.request.type.name} | State: ${s.request.state()}</a>
                            </div>
	                    </div>
	                    <br/>
	                %endfor
	            %endif
            </div>
        </form>
    </div>
</div>
