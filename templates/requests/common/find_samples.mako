<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${h.js("libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging" )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>

<% is_admin = cntrller == 'requests_admin' and trans.user_is_admin() %>

<br/>
<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller=cntrller, action='browse_requests' )}">Browse requests</a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Find samples</div>
    <div class="toolFormBody">
        <form name="find_request" id="find_request" action="${h.url_for( controller='requests_common', action='find_samples', cntrller=cntrller )}" method="post" >
            <div class="form-row">
                <label>Find samples using:</label>
                ${search_type.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Select a sample attribute for searching.  To search <br/>
                    for a sample with a dataset name, select the dataset <br/>
                    option above. This will return all the samples that <br/>
                    are associated with a dataset with that name. <br/> 
                </div>
            </div>
            <div class="form-row">
                <label>Show only sequencing requests in state:</label>
                ${request_states.get_html()}
            </div>
            <div class="form-row">
                ${search_box.get_html()}
                <input type="submit" name="find_samples_button" value="Find"/>  
                <div class="toolParamHelp" style="clear: both;">
                   <p>
                   Wildcard search (%) can be used as placeholder for any sequence of characters or words.<br/> 
                   For example, to search for samples starting with 'mysample' use 'mysample%' as the search string.
                   </p>
                   <p>
                   When 'form value' search type is selected, then enter the search string in 'field label=value' format.
                   <br/>For example, when searching for all samples whose 'Volume' field is 1.3mL, then the search string
                   should be 'Volume=1.3mL' (without qoutes).
                   </p>
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
                    %for sample in samples:
                        <div class="form-row">
                            Sample: <b>${sample.name}</b> | Barcode: ${sample.bar_code}<br/>
                            %if sample.request.is_new or not sample.state:
                                State: Unsubmitted<br/>
                            %else:
                                State: ${sample.state.name}<br/>
                            %endif
                            <%
                                # Get an external_service from one of the sample datasets.  This assumes all sample datasets are associated with
                                # the same external service - hopefully this is a good assumption.
                                external_service = sample.datasets[0].external_service
                            %>
                            Datasets: <a href="${h.url_for( controller='requests_common', action='view_sample_datasets', cntrller=cntrller, external_service_id=trans.security.encode_id( external_service.id ), sample_id=trans.security.encode_id( sample.id ) )}">${len( sample.datasets )}</a><br/>
                            %if is_admin:
                               <i>User: ${sample.request.user.email}</i>
                            %endif
                            <div class="toolParamHelp" style="clear: both;">
                                <a href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Sequencing request: ${sample.request.name} | Type: ${sample.request.type.name} | State: ${sample.request.state}</a>
                            </div>
                        </div>
                        <br/>
                    %endfor
                %endif
            </div>
        </form>
    </div>
</div>
