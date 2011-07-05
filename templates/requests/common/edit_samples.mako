<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/common/common.mako" import="common_javascripts" />
<%namespace file="/requests/common/common.mako" import="render_samples_grid" />
<%namespace file="/requests/common/common.mako" import="render_request_type_sample_form_grids" />
<%namespace file="/requests/common/common.mako" import="render_samples_messages" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
   ${parent.javascripts()}
   ${common_javascripts()}
   ${local_javascripts()}
</%def>

<%def name="local_javascripts()">
    <script type="text/javascript">
	    // This function stops the form from getting submitted when return key is pressed
	    // This is needed in this form as the barcode scanner (when in keyboard emulation mode)
	    // may send a return key appended to the scanned barcode string.  
	    function stopRKey(evt) {
	      var evt = (evt) ? evt : ((event) ? event : null);
	      var node = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
	      if ((evt.keyCode == 13) && (node.type=="text"))  {return false;}
	    }
	    document.onkeypress = stopRKey
    </script>
</%def>

<%
    from galaxy.web.framework.helpers import time_ago

    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    is_complete = request.is_complete
    is_submitted = request.is_submitted
    is_unsubmitted = request.is_unsubmitted
    if is_admin:
        can_add_samples = not is_complete
    else:
        can_add_samples = is_unsubmitted
    can_delete_samples = request.samples and not is_complete
    can_edit_request = ( is_admin and not request.is_complete ) or request.is_unsubmitted
    can_reject = is_admin and is_submitted
    can_submit = request.samples and is_unsubmitted
%>

<br/><br/>

<ul class="manage-table-actions">
    %if can_add_samples:
        <li><a class="action-button" href="${h.url_for( controller='requests_common', action='add_sample', cntrller=cntrller, request_id=trans.security.encode_id( request.id ), add_sample_button='Add sample' )}">Add sample</a></li>
    %endif
    %if can_submit:
        <li><a class="action-button" confirm="More samples cannot be added to this request after it is submitted. Click OK to submit." href="${h.url_for( controller='requests_common', action='submit_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Submit request</a></li>
    %endif
    <li><a class="action-button" id="request-${request.id}-popup" class="menubutton">Request Actions</a></li>
    <div popupmenu="request-${request.id}-popup">
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Browse this request</a>
        %if can_edit_request:
            <a class="action-button" href="${h.url_for( controller='requests_common', action='edit_basic_request_info', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Edit this request</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request_history', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">View history</a>
        %if can_reject:
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='reject_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Reject this request</a>
        %endif
    </div>
</ul>

${render_samples_messages(request, is_admin, is_submitted, message, status)}

<div class="toolFormBody">
    <form id="edit_samples" name="edit_samples" action="${h.url_for( controller='requests_common', action='edit_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}" method="post">
        %if displayable_sample_widgets:
            <%
                grid_header = '<h3>Edit Current Samples of Sequencing Request "%s"</h3>' % request.name
            %>
            ${render_samples_grid( cntrller, request, displayable_sample_widgets, action='edit_samples', encoded_selected_sample_ids=encoded_selected_sample_ids, render_buttons=False, grid_header=grid_header )}
            %if len( sample_operation_select_field.options ) > 1 and not is_unsubmitted:
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
                        %elif sample_operation_selected_value == trans.app.model.Sample.bulk_operations.SELECT_LIBRARY:
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
            <div class="toolParamHelp" style="clear: both;">
                For each sample, select the data library and folder in which you would like the run datasets deposited.
                To automatically run a workflow on run datastets, select a history first and then the desired workflow. 
            </div>
            ## Render the other grids
            <% trans.sa_session.refresh( request.type.sample_form ) %>
            %for grid_index, grid_name in enumerate( request.type.sample_form.layout ):
                ${render_request_type_sample_form_grids( grid_index, grid_name, request.type.sample_form.grid_fields( grid_index ), displayable_sample_widgets=displayable_sample_widgets, show_saved_samples_read_only=False )}
            %endfor
        %else:
            <label>There are no samples.</label>
        %endif  
        <p/>
        <div class="form-row">
            ## hidden element to make twill work.
            ## Greg will fix this
            <input type="hidden" name="twill" value=""/>
            <input type="submit" name="save_samples_button" value="Save"/>
            <input type="submit" name="cancel_changes_button" value="Cancel"/>
            <div class="toolParamHelp" style="clear: both;">
            Click the <b>Save</b> button when you have finished editing the samples
        </div>
        %if request.samples and request.is_submitted:
            <script type="text/javascript">
                // Updater
                sample_state_updater( {${ ",".join( [ '"%s" : "%s"' % ( s.id, s.state.name ) for s in request.samples ] ) }});
            </script>
        %endif
    </form>
</div>
