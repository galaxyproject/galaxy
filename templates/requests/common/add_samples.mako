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
    can_edit_samples = request.samples and ( is_admin or not is_complete )
    can_edit_request = ( is_admin and not request.is_complete ) or request.is_unsubmitted
    can_reject = is_admin and is_submitted
    can_submit = request.samples and is_unsubmitted
%>

<br/><br/>

<ul class="manage-table-actions">
    %if can_edit_samples:
        <li><a class="action-button" href="${h.url_for( controller='requests_common', action='edit_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Edit samples</a></li>
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
    <form id="add_samples" name="add_samples" action="${h.url_for( controller='requests_common', action='add_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}" method="post">
        %if displayable_sample_widgets:
            <%
                grid_header = '<h3>Add samples to sequencing request "%s"</h3>' % request.name
            %>
            ${render_samples_grid( cntrller, request, displayable_sample_widgets, action='edit_samples', adding_new_samples=True, encoded_selected_sample_ids=[], render_buttons=False, grid_header=grid_header )}
            <div class="toolParamHelp" style="clear: both;">
                For each sample, select the data library and folder in which you would like the run datasets deposited.
                To automatically run a workflow on run datastets, select a history first and then the desired workflow. 
            </div>
            ## Render the other grids
            <% trans.sa_session.refresh( request.type.sample_form ) %>
            %for grid_index, grid_name in enumerate( request.type.sample_form.layout ):
                ${render_request_type_sample_form_grids( grid_index, grid_name, request.type.sample_form.grid_fields( grid_index ), displayable_sample_widgets=displayable_sample_widgets, show_saved_samples_read_only=True )}
            %endfor
        %else:
            <label>There are no samples.</label>
        %endif  
        %if can_add_samples:
            ## The user is adding a new sample
            %if displayable_sample_widgets:
                <p/>
                <div class="form-row">
                    <label> Copy <input type="text" name="num_sample_to_copy" value="1" size="3"/> samples from sample ${sample_copy_select_field.get_html()}</label>
                    <div class="toolParamHelp" style="clear: both;">
                        Select the sample from which the new sample should be copied or leave selection as <b>None</b> to add a new "generic" sample.
                    </div>
                </div>
            %endif
            <p/>
            <div class="form-row">
                <input type="hidden" name="twill" value=""/>
                %if ( request.samples or displayable_sample_widgets ) and len( displayable_sample_widgets ) > len( request.samples ):
                    <input type="submit" name="add_sample_button" value="Add sample" />
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
        %endif
    </form>
</div>
%if is_unsubmitted:
    <p/>
    <h4><img src="/static/images/silk/resultset_next.png" alt="Hide" onclick="showContent(this);" style="cursor:pointer;"/>Import samples from csv file</h4>
    <div style="display:none;">
        <div class="toolFormBody">
            <form id="import" name="import" action="${h.url_for( controller='requests_common', action='add_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}" enctype="multipart/form-data" method="post" >
                <div class="form-row">
                    <input type="file" name="file_data" />
                    <input type="submit" name="import_samples_button" value="Import samples"/>
                    <div class="toolParamHelp" style="clear: both;">
                        The csv file must be in the following format.<br/>
                        The [:FieldValue] is optional, the named form field will contain the value after the ':' if included.<br/>
                        SampleName,DataLibraryName,FolderName,HistoryName,WorkflowName,Field1Name:Field1Value,Field2Name:Field2Value...
                    </div>
                </div>
            </form>
        </div>
    </div>
%endif
