<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/common/common.mako" import="common_javascripts" />
<%namespace file="/requests/common/common.mako" import="render_samples_grid" />
<%namespace file="/requests/common/common.mako" import="render_request_type_sample_form_grids" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
   ${parent.javascripts()}
   ${common_javascripts()}
</%def>

<%
    from galaxy.web.framework.helpers import time_ago

    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    is_complete = request.is_complete
    is_unsubmitted = request.is_unsubmitted
    can_add_samples = is_unsubmitted
    can_delete_samples = request.samples and not is_complete
    can_edit_samples = request.samples and ( is_admin or not is_complete )
    can_edit_request = ( is_admin and not request.is_complete ) or request.is_unsubmitted
    can_reject_or_transfer = is_admin and request.is_submitted
    can_submit = request.samples and is_unsubmitted
%>

<br/><br/>

<ul class="manage-table-actions">
    %if not editing_samples and can_edit_samples:
        <li><a class="action-button" href="${h.url_for( controller='requests_common', action='edit_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ), editing_samples='True' )}">Edit samples</a></li>
    %endif
    %if editing_samples and can_add_samples:
        <li><a class="action-button" href="${h.url_for( controller='requests_common', action='add_sample', cntrller=cntrller, request_id=trans.security.encode_id( request.id ), add_sample_button='Add sample' )}">Add sample</a></li>
    %endif
    %if can_submit:
        <li><a class="action-button" confirm="More samples cannot be added to this request after it is submitted. Click OK to submit." href="${h.url_for( controller='requests_common', action='submit_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Submit request</a></li>
    %endif
    <li><a class="action-button" id="request-${request.id}-popup" class="menubutton">Request actions</a></li>
    <div popupmenu="request-${request.id}-popup">
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Browse this request</a>
        %if can_edit_request:
            <a class="action-button" href="${h.url_for( controller='requests_common', action='edit_basic_request_info', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Edit</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='requests_common', action='request_events', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">View history</a>
        %if can_reject_or_transfer:
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='reject_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Reject</a>
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='get_data', request_id=trans.security.encode_id( request.id ) )}">Select datasets to transfer</a>
        %endif
    </div>
</ul>

%if request.samples_without_library_destinations:
    <br/>
    <font color="red"><b><i>Select a target data library and folder for all samples before starting the sequence run</i></b></font>
    <br/>
%endif

%if request.is_rejected:
    <br/>
    <font color="red"><b><i>Reason for rejection: </i></b></font><b>${request.last_comment}</b>
    <br/>
%endif

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolFormBody">
    <form id="edit_samples" name="edit_samples" action="${h.url_for( controller='requests_common', action='edit_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ), editing_samples=editing_samples )}" method="post">
        %if current_samples:
            <%
                if editing_samples:
                    grid_header = '<h3>Edit Current Samples of Request "%s"</h3>' % request.name
                else:
                    grid_header = '<h3>Add Samples to Request "%s"</h3>' % request.name
            %>
            ${render_samples_grid( cntrller, request, current_samples, action='edit_samples', editing_samples=editing_samples, encoded_selected_sample_ids=encoded_selected_sample_ids, render_buttons=False, grid_header=grid_header )}
            %if editing_samples and len( sample_operation_select_field.options ) > 1 and not is_unsubmitted:
                <div class="form-row" style="background-color:#FAFAFA;">
                    For selected samples: 
                    ${sample_operation_select_field.get_html()}
                </div>
                <% sample_operation_selected_value = sample_operation_select_field.get_selected( return_value=True ) %>
                %if ( is_admin or not is_complete ) and sample_operation_selected_value != 'none' and encoded_selected_sample_ids:
                    <div class="form-row" style="background-color:#FAFAFA;">
                        %if sample_operation_selected_value == trans.model.Sample.bulk_operations.CHANGE_STATE:
                            ## sample_operation_selected_value == 'Change state'
                            <div class="form-row">
                                <label>Change current state</label>
                                ${sample_state_id_select_field.get_html()}
                                <label>Comments</label>
                                <input type="text" name="sample_event_comment" value=""/>
                                <div class="toolParamHelp" style="clear: both;">
                                    Optional
                                </div>
                            </div>
                        %elif not is_complete and sample_operation_selected_value == trans.app.model.Sample.bulk_operations.SELECT_LIBRARY:
                        <% libraries_selected_value = libraries_select_field.get_selected( return_value=True ) %>
                            <div class="form-row">
    	                        <label>Select data library:</label>
    	                        ${libraries_select_field.get_html()}
                            </div>
                            %if libraries_selected_value != 'none':
                                <div class="form-row">
    		                        <label>Select folder:</label>
    		                        ${folders_select_field.get_html()}
    	                        </div>
                            %endif
                        %endif
                    </div>
                %endif
            %endif
            ## Render the other grids
            <% trans.sa_session.refresh( request.type.sample_form ) %>
            %for grid_index, grid_name in enumerate( request.type.sample_form.layout ):
                ${render_request_type_sample_form_grids( grid_index, grid_name, request.type.sample_form.grid_fields( grid_index ), editing_samples=editing_samples )}
            %endfor
        %else:
            <label>There are no samples.</label>
        %endif  
        %if not editing_samples and is_unsubmitted:
            ## The user is adding a new sample
            %if current_samples:
                <p/>
                <div class="form-row">
                    <label> Copy <input type="text" name="num_sample_to_copy" value="1" size="3"/> samples from sample ${sample_copy.get_html()}</label>
                    <div class="toolParamHelp" style="clear: both;">
                        Select the sample from which the new sample should be copied or leave selection as <b>None</b> to add a new "generic" sample.
                    </div>
                </div>
            %endif
            <p/>
            <div class="form-row">
                %if ( request.samples or current_samples ) and ( editing_samples or len( current_samples ) > len( request.samples ) ):
                    <input type="submit" name="add_sample_button" value="Add sample"/>
                    <input type="submit" name="save_samples_button" value="Save"/>
                    <input type="submit" name="cancel_changes_button" value="Cancel"/>
                    <div class="toolParamHelp" style="clear: both;">
                        Click the <b>Add sample</b> button for each new sample and click the <b>Save</b> button when you have finished adding samples.
                    </div>
                %else:
                    <input type="submit" name="add_sample_button" value="Add sample"/>
                    <div class="toolParamHelp" style="clear: both;">
                        Click the <b>Add sample</b> button for each new sample.
                    </div>
                %endif
            </div>
        %elif editing_samples:
            <p/>
            <div class="form-row">
                <input type="submit" name="save_samples_button" value="Save"/>
                <input type="submit" name="cancel_changes_button" value="Cancel"/>
                <div class="toolParamHelp" style="clear: both;">
                Click the <b>Save</b> button when you have finished editing the samples
            </div>
        %endif
        %if request.samples and request.is_submitted:
            <script type="text/javascript">
                // Updater
                updater( {${ ",".join( [ '"%s" : "%s"' % ( s.id, s.state.name ) for s in request.samples ] ) }});
            </script>
        %endif
    </form>
</div>
%if is_unsubmitted and not editing_samples:
    <p/>
    ##<div class="toolForm">
        ##<div class="toolFormTitle">Import samples from csv file</div>
        <h4><img src="/static/images/fugue/toggle-expand.png" alt="Hide" onclick="showContent(this);" style="cursor:pointer;"/> Import samples from csv file</h4>
        <div style="display:none;">
            <div class="toolFormBody">
                <form id="import" name="import" action="${h.url_for( controller='requests_common', action='edit_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ), editing_samples=editing_samples )}" enctype="multipart/form-data" method="post" >
                    <div class="form-row">
                        <input type="file" name="file_data" />
                        <input type="submit" name="import_samples_button" value="Import samples"/>
                        <div class="toolParamHelp" style="clear: both;">
                            The csv file must be in the following format:<br/>
                            SampleName,DataLibrary,DataLibraryFolder,FieldValue1,FieldValue2...
                        </div>
                    </div>
                </form>
            </div>
        </div>
    ##</div>
%endif
