<%namespace file="/requests/common/sample_state.mako" import="render_sample_state" />

<%def name="javascripts()">
   ${self.common_javascripts()}
</%def>

<%def name="common_javascripts()">
    <script type="text/javascript">
        function showContent(vThis)
        {
            // http://www.javascriptjunkie.com
            // alert(vSibling.className + " " + vDef_Key);
            vParent = vThis.parentNode;
            vSibling = vParent.nextSibling;
            while (vSibling.nodeType==3) { 
                // Fix for Mozilla/FireFox Empty Space becomes a TextNode or Something
                vSibling = vSibling.nextSibling;
            };
            if(vSibling.style.display == "none")
            {
                vThis.src="/static/images/fugue/toggle.png";
                vThis.alt = "Hide";
                vSibling.style.display = "block";
            } else {
                vSibling.style.display = "none";
                vThis.src="/static/images/fugue/toggle-expand.png";
                vThis.alt = "Show";
            }
            return;
        }
        $(document).ready(function(){
            //hide the all of the element with class msg_body
            $(".msg_body").hide();
            //toggle the component with class msg_body
            $(".msg_head").click(function(){
                $(this).next(".msg_body").slideToggle(0);
            });
        });

        function checkAllFields()
        {
            var chkAll = document.getElementById('checkAll');
            var checks = document.getElementsByTagName('input');
            var boxLength = checks.length;
            var allChecked = false;
            var totalChecked = 0;
            if ( chkAll.checked == true )
            {
                for ( i=0; i < boxLength; i++ )
                {
                    if ( checks[i].name.indexOf( 'select_sample_' ) != -1)
                    {
                       checks[i].checked = true;
                    }
                }
            }
            else
            {
                for ( i=0; i < boxLength; i++ )
                {
                    if ( checks[i].name.indexOf( 'select_sample_' ) != -1)
                    {
                       checks[i].checked = false
                    }
                }
            }
        }

        // Looks for changes in sample states using an async request. Keeps
        // calling itself (via setTimeout) until all samples are in a terminal
        // state.
        var updater = function ( sample_states ) {
            // Check if there are any items left to track
            var empty = true;
            for ( i in sample_states ) {
                empty = false;
                break;
            }
            if ( ! empty ) {
                setTimeout( function() { updater_callback( sample_states ) }, 1000 );
            }
        };

        var updater_callback = function ( sample_states ) {
            // Build request data
            var ids = []
            var states = []
            $.each( sample_states, function ( id, state ) {
                ids.push( id );
                states.push( state );
            });
            // Make ajax call
            $.ajax( {
                type: "POST",
                url: "${h.url_for( controller='requests_common', action='sample_state_updates' )}",
                dataType: "json",
                data: { ids: ids.join( "," ), states: states.join( "," ) },
                success : function ( data ) {
                    $.each( data, function( id, val ) {
                        // Replace HTML
                        var cell1 = $("#sampleState-" + id);
                        cell1.html( val.html_state );
                        var cell2 = $("#sampleDatasets-" + id);
                        cell2.html( val.html_datasets );
                        sample_states[ parseInt( id ) ] = val.state;
                    });
                    updater( sample_states ); 
                },
                error: function() {
                    // Just retry, like the old method, should try to be smarter
                    updater( sample_states );
                }
            });
        };
    </script>
</%def>

<%def name="render_editable_sample_row( is_admin, sample, current_sample_index, current_sample, encoded_selected_sample_ids )">
    <%
        if sample:
            trans.sa_session.refresh( sample.request )
            is_complete = sample.request.is_complete
            is_rejected = request.is_rejected
            is_submitted = sample.request.is_submitted
            is_unsubmitted = sample.request.is_unsubmitted
            display_checkboxes = editing_samples and ( is_complete or is_rejected or is_submitted )
            display_bar_code = request.samples and ( is_complete or is_rejected or is_submitted )
            display_datasets = request.samples and ( is_complete or is_rejected or is_submitted )
        else:
            is_complete = False
            is_submitted = False
            is_unsubmitted = False
            display_checkboxes = False
    %>
    <%
        if display_checkboxes and trans.security.encode_id( sample.id ) in encoded_selected_sample_ids:
            checked_str = "checked"
        else:
            checked_str = ""
    %>
    %if display_checkboxes:
        <td><input type="checkbox" name=select_sample_${sample.id} id="sample_checkbox" value="true" ${checked_str}/><input type="hidden" name=select_sample_${sample.id} id="sample_checkbox" value="true"/></td>
    %endif
    <td valign="top">
        <input type="text" name="sample_${current_sample_index}_name" value="${current_sample['name']}" size="10"/>
        <div class="toolParamHelp" style="clear: both;">
            <i>${' (required)' }</i>
        </div>
    </td>
    %if display_bar_code:
        <td valign="top">
            %if is_admin:
                <input type="text" name="sample_${current_sample_index}_barcode" value="${current_sample['barcode']}" size="10"/>
            %else:
                ${current_sample['barcode']}
                <input type="hidden" name="sample_${current_sample_index}_barcode" value="${current_sample['barcode']}"/>
            %endif
        </td>
    %endif 
    %if sample:
        %if is_unsubmitted:
            <td>Unsubmitted</td>
        %else:
            <td valign="top"><a href="${h.url_for( controller='requests_common', action='sample_events', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">${sample.state.name}</a></td>
        %endif    
    %else:
        <td></td>
    %endif
    <td valign="top">${current_sample['library_select_field'].get_html()}</td>
    <td valign="top">${current_sample['folder_select_field'].get_html()}</td>
    %if display_datasets: 
        <%
            if sample:
                label = str( len( sample.datasets ) )
            else:
                label = 'add'
        %>
        <td valign="top"><a href="${h.url_for( controller='requests_common', action='view_dataset_transfer', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">${label}</a></td>
        <td valign="top"><a href="${h.url_for( controller='requests_common', action='view_dataset_transfer', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">${label}</a></td>
    %endif
    %if sample and ( is_admin or is_unsubmitted ) and not is_complete:
        ## Delete button
        <td valign="top"><a class="action-button" href="${h.url_for( controller='requests_common', action='delete_sample', cntrller=cntrller, request_id=trans.security.encode_id( request.id ), sample_id=current_sample_index )}"><img src="${h.url_for('/static/images/delete_icon.png')}" style="cursor:pointer;"/></a></td>
    %endif
</%def>

<%def name="render_samples_grid( cntrller, request, current_samples, action, editing_samples=False, encoded_selected_sample_ids=[], render_buttons=False, grid_header='<h3>Samples</h3>' )">
    ## Displays the "Samples" grid
    <%
        trans.sa_session.refresh( request )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        is_complete = request.is_complete
        is_rejected = request.is_rejected
        is_submitted = request.is_submitted
        is_unsubmitted = request.is_unsubmitted
        can_add_samples = request.is_unsubmitted
        can_delete_samples = request.samples and not is_complete
        can_edit_samples = request.samples and ( is_admin or not is_complete )
        display_checkboxes = editing_samples and ( is_complete or is_rejected or is_submitted )
        display_bar_code = request.samples and ( is_complete or is_rejected or is_submitted )
        display_datasets = request.samples and ( is_complete or is_rejected or is_submitted )
    %>
    ${grid_header}
    %if render_buttons and ( can_add_samples or can_edit_samples ):
        <ul class="manage-table-actions">
            %if can_add_samples:
                <li><a class="action-button" href="${h.url_for( controller='requests_common', action='add_sample', cntrller=cntrller, request_id=trans.security.encode_id( request.id ), add_sample_button='Add sample' )}">Add sample</a></li>
            %endif
            %if can_edit_samples:
                <li><a class="action-button" href="${h.url_for( controller='requests_common', action='edit_samples', cntrller=cntrller, id=trans.security.encode_id( request.id ), editing_samples='True' )}">Edit samples</a></li>
            %endif
        </ul>
    %endif
    <table class="grid">
        <thead>
            <tr>
                %if display_checkboxes:
                    <th><input type="checkbox" id="checkAll" name=select_all_samples_checkbox value="true" onclick='checkAllFields(1);'/><input type="hidden" name=select_all_samples_checkbox value="true"/></th>
                %endif
                <th>Name</th>
                %if display_bar_code:
                    <th>Barcode</th>
                %endif
                <th>State</th>
                <th>Data Library</th>
                <th>Folder</th>
                %if display_datasets:
                    <th>Datasets Selected</th>
                    <th>Datasets Transferred</th>
                %endif
                <th>
                    %if can_delete_samples:
                        Delete
                    %endif
                </th>
            </tr>
        <thead>
        <tbody>
            <% trans.sa_session.refresh( request ) %>
            ## current_samples is a dictionary whose keys are:
            ## name, barcode, library, folder, field_values, library_select_field, folder_select_field
            %for current_sample_index, current_sample in enumerate( current_samples ):
                <%
                    current_sample_name = current_sample[ 'name' ]
                    current_sample_barcode = current_sample[ 'barcode' ]
                    current_sample_library = current_sample[ 'library' ]
                    if current_sample_library:
                        if cntrller == 'requests':
                            library_cntrller = 'library'
                        elif is_admin:
                            library_cntrller = 'library_admin'
                        else:
                            library_cntrller = None
                    current_sample_folder = current_sample[ 'folder' ]
                    try:
                        sample = request.samples[ current_sample_index ]
                    except:
                        sample = None 
                %>
                %if editing_samples:
                    <tr>${render_editable_sample_row( is_admin, sample, current_sample_index, current_sample, encoded_selected_sample_ids )}</tr>
                %elif sample:
                    <tr>
                        <td>${current_sample_name}</td>
                        %if display_bar_code:
                            <td>${current_sample_barcode}</td>
                        %endif
                        %if is_unsubmitted:
                            <td>Unsubmitted</td>
                        %else:
                            <td><a id="sampleState-${sample.id}" href="${h.url_for( controller='requests_common', action='sample_events', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">${render_sample_state( sample )}</a></td>
                        %endif
                        %if current_sample_library and library_cntrller is not None:
                            <td><a href="${h.url_for( controller='library_common', action='browse_library', cntrller=library_cntrller, id=trans.security.encode_id( current_sample_library.id ) )}">${current_sample_library.name}</a></td>                                  
                        %else:
                            <td></td>
                        %endif
                        %if current_sample_folder:
                            <td>${current_sample_folder.name}</td>
                        %else:
                            <td></td>
                        %endif
                        %if is_submitted or is_complete: 
                            <td><a id="sampleDatasets-${sample.id}" href="${h.url_for( controller='requests_common', action='view_dataset_transfer', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">${len( sample.datasets )}</a></td>
                            <td><a id="sampleDatasets-${sample.id}" href="${h.url_for( controller='requests_common', action='view_dataset_transfer', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">${len( sample.transferred_dataset_files )}</a></td>
                        %endif
                    </tr>
                %else:
                    ## The Add sample button was clicked for this sample_widget
                    <tr>${render_editable_sample_row( is_admin, None, current_sample_index, current_sample, encoded_selected_sample_ids )}</tr>
                %endif
            %endfor
        </tbody>
    </table>
</%def>

<%def name="render_sample_form( index, sample_name, sample_values, fields_dict, display_only )">
    <tr>
        <td>${sample_name}</td>
        %for field_index, field in fields_dict.items():
            <% field_type = field[ 'type' ] %>
            <td>
                %if display_only:
                    %if sample_values[field_index]:
                        %if field_type == 'WorkflowField':
                            %if str(sample_values[field_index]) != 'none':
                                <% workflow = trans.sa_session.query( trans.app.model.StoredWorkflow ).get( int( sample_values[ field_index ] ) ) %>
                                <a href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id( workflow.id ) )}">${workflow.name}</a>
                            %endif
                        %else:
                            ${sample_values[ field_index ]}
                        %endif
                    %else:
                        <i>None</i>
                    %endif
                %else:
                    %if field_type == 'TextField':
                        <input type="text" name="sample_${index}_field_${field_index}" value="${sample_values[field_index]}" size="7"/>
                    %elif field_type == 'SelectField':
                        <select name="sample_${index}_field_${field_index}" last_selected_value="2">
                            %for option_index, option in enumerate(field['selectlist']):
                                %if option == sample_values[field_index]:
                                    <option value="${option}" selected>${option}</option>
                                %else:
                                    <option value="${option}">${option}</option>
                                %endif
                            %endfor
                        </select>
                    %elif field_type == 'WorkflowField':
                        <select name="sample_${index}_field_${field_index}">
                            %if str(sample_values[field_index]) == 'none':
                                <option value="none" selected>Select one</option>
                            %else:
                                <option value="none">Select one</option>
                            %endif
                            %for option_index, option in enumerate(request.user.stored_workflows):
                                %if not option.deleted:
                                    %if str(option.id) == str(sample_values[field_index]):
                                        <option value="${option.id}" selected>${option.name}</option>
                                    %else:
                                        <option value="${option.id}">${option.name}</option>
                                    %endif
                                %endif
                            %endfor
                        </select>
                    %elif field_type == 'CheckboxField':
                        <input type="checkbox" name="sample_${index}_field_${field_index}" value="Yes"/>
                    %endif
                    <div class="toolParamHelp" style="clear: both;">
                        <i>${'('+field['required']+')' }</i>
                    </div>
                %endif
            </td>
        %endfor
    </tr> 
</%def>

<%def name="render_request_type_sample_form_grids( grid_index, grid_name, fields_dict, editing_samples )">
    <%
        if not grid_name:
            grid_name = "Sample form layout " + grid_index
    %>
    <h4><img src="/static/images/fugue/toggle-expand.png" alt="Hide" onclick="showContent(this);" style="cursor:pointer;"/> ${grid_name}</h4>
    <div style="display:none;">
        <table class="grid">
            <thead>
                <tr>
                    <th>Name</th>
                    %for index, field in fields_dict.items():
                        <th>
                            ${field['label']}
                            ## TODO: help comments in the grid header are UGLY!
                            ## If they are needed display them more appropriately,
                            ## if they are not, delete this commented code.
                            ##<div class="toolParamHelp" style="clear: both;">
                            ##    <i>${field['helptext']}</i>
                            ##</div>
                        </th>
                    %endfor
                    <th></th>
                </tr>
            <thead>
            <tbody>
                <% trans.sa_session.refresh( request ) %>
                %for sample_index, sample in enumerate( current_samples ):
                    <%
                        if editing_samples or sample_index >= len( request.samples ):
                            display_only = False
                        else:
                            display_only = True
                    %>
                    ${render_sample_form( sample_index, sample['name'], sample['field_values'], fields_dict, display_only )}    
                %endfor
            </tbody>
        </table>
    </div>
</%def>
