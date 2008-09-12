<%def name="render_permissions_forms( data_obj )">
<script type="text/javascript">
    var q = jQuery.noConflict();
    q( document ).ready( function () {
        // initialize state
        q("input.groupCheckbox").each( function() {
            if ( ! q(this).is(":checked") ) q("div#group_" + this.value).hide();
        });
        // handle events
        q("input.groupCheckbox").click( function() {
            if ( q(this).is(":checked") ) {
                q("div#group_" + this.value).slideDown("fast");
            } else {
                q("div#group_" + this.value).slideUp("fast");
            }
        });
    });
</script>

<%
    redirect = None
    id = None
    if isinstance( data_obj, trans.app.model.LibraryFolderDatasetAssociation ):
        dataset = data_obj.dataset
        redirect = ("lid", data_obj.id)
    elif isinstance( data_obj, list ):
        dataset = data_obj[0].dataset
        id = ",".join( [ str(d.dataset.id) for d in data_obj ] )
        if isinstance( data_obj[0], trans.app.model.LibraryFolderDatasetAssociation ):
            redirect = ("lid", ",".join( [ str(d.id) for d in data_obj ] ) )
    else:
        trans.show_error_message( "Unknown object passed to render_permissions_forms" )
    if id is None:
        id = dataset.id
%>

<div class="toolForm">
    <div class="toolFormTitle">Change Existing Permissions</div>
    <div class="toolFormBody">
        <form name="edit_group_associations" action="${h.url_for( controller='admin', action='dataset_permissions' )}" method="post">
            <input type="hidden" name="id" value="${id}">
            %if redirect:
                <input type="hidden" name="${redirect[0]}" value="${redirect[1]}">
            %endif
            <div class="form-row">
                <%
                    user_permissions = [ p for p in trans.app.security_agent.get_dataset_permissions( dataset ) if p[0].name.endswith( ' private group' ) ]
                    real_permissions = [ p for p in trans.app.security_agent.get_dataset_permissions( dataset ) if not p[0].name.endswith( ' private group' ) and p[0].name != 'public' ]
                %>
                <div class="toolParamHelp" style="clear: both;">
                    Update the permissions for the users and groups currently associated with this dataset.
                </div>
                <br/>
                %if trans.app.security_agent.dataset_has_group( dataset.id, trans.app.security_agent.get_public_group().id ):
                    <label>Allow public access:</label><br/>
                    <input type="checkbox" name="public" value="Yes" checked>  This dataset can be accessed by anyone (it is public).<br/>
                %endif
                <br/>
                <label>Users with permissions on this dataset:</label><br/>
                %if not len( user_permissions ):
                    &nbsp;&nbsp;None<br/>
                %endif
                %for p in user_permissions:
                    <input type="checkbox" name="users" class="groupCheckbox" value="${p[0].id}" checked/> ${p[0].name.replace( ' private group', '' )} <br/>
                    <div class="permissionContainer" id="group_${p[0].id}">
                        %for k, v in trans.app.security_agent.permitted_actions.items():
                            <input type="checkbox" name="actions" value="${p[0].id},${k}"
                            %if v in p[1]:
                                checked
                            %endif
                            /> ${trans.app.security_agent.get_permitted_action_description(k)} <br/>
                        %endfor
                    </div>
                %endfor
                <br/>
                <label>Groups with permissions on this dataset:</label><br/>
                %if not len( real_permissions ):
                    &nbsp;&nbsp;None<br/>
                %endif
                %for p in real_permissions:
                    <input type="checkbox" name="groups" class="groupCheckbox" value="${p[0].id}" checked/> ${p[0].name} <br/>
                    <div class="permissionContainer" id="group_${p[0].id}">
                        %for k, v in trans.app.security_agent.permitted_actions.items():
                            <input type="checkbox" name="actions" value="${p[0].id},${k}"
                            %if v in p[1]:
                                checked
                            %endif
                            /> ${trans.app.security_agent.get_permitted_action_description(k)} <br/>
                        %endfor
                    </div>
                %endfor
                <br/>
            </div>
            <div class="form-row"><input type="submit" name="change_permitted_actions" value="Save"></div>
        </form>
    </div>
</div>
<p/>

<div class="toolForm">
    <div class="toolFormTitle">Add New Users and Groups</div>
    <div class="toolFormBody">
        <form name="make_new_group_associations" action="${h.url_for( controller='admin', action='dataset_permissions' )}" method="post">
            <input type="hidden" name="id" value="${id}">
            %if redirect:
                <input type="hidden" name="${redirect[0]}" value="${redirect[1]}">
            %endif
            <div class="form-row">
                <div class="toolParamHelp" style="clear: both;">
                    Select new users and groups to associate with this dataset (you can assign permissions after creating the association).
                </div>
                ## Don't display the public access checkbox if it's already public (it's shown above instead)
                %if not trans.app.security_agent.dataset_has_group( dataset.id, trans.app.security_agent.get_public_group().id ):
                    <label>Allow public access:</label><br/>
                    <input type="checkbox" name="public" value="Yes">  This dataset can be accessed by anyone (make it public).<br/>
                %endif
                <br/>
                <%
                    all_groups = trans.app.model.Group.select()
                    user_groups = [ g for g in all_groups if g.name.endswith( ' private group' ) ]
                    real_groups = [ g for g in all_groups if not g.name.endswith( ' private group' ) and g.name != 'public' ]
                %>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <label>Associate with users:</label>
                    <select name="users" multiple="true" size="5">
                        %for group in user_groups:
                            %if not trans.app.security_agent.dataset_has_group( dataset.id, group.id ):
                                <option value="${group.id}">${group.name.replace( ' private group', '' )}</option>
                            %endif 
                        %endfor
                    </select>
                    <p/>
                    <label>Associate with groups:</label>
                    <select name="groups" multiple="true" size="5">
                        %for group in real_groups:
                            %if dataset and not trans.app.security_agent.dataset_has_group( dataset.id, group.id ):
                                <option value="${group.id}">${group.name}</option>
                            %endif
                        %endfor
                    </select>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    To select multiple users or groups, hold ctrl or command while clicking.
                </div>
            </div>
            <div class="form-row"><input type="submit" name="create_group_associations" value="Save"></div>
        </form>
    </div>
</div>
<p/>

</%def>

<%doc>
    Shamelessly stolen from history... this needs to be cleaned up to remove a
    bunch of stuff that doesn't apply to library datasets (like state, etc).
</%doc>

## Render the dataset `data`
<%def name="render_dataset( data )">
    <%
	if data.state in ['no state','',None]:
	    data_state = "queued"
	else:
	    data_state = data.state
    %>
    %if not trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset = data.dataset ):
        <div class="historyItemWrapper historyItem historyItem-${data_state} historyItem-noPermission" id="historyItem-${data.id}">
    %else:
        <div class="historyItemWrapper historyItem historyItem-${data_state}" id="historyItem-${data.id}">
    %endif
        
        ## Header row for history items (name, state, action buttons)
        
	<div style="overflow: hidden;" class="historyItemTitleBar">
	    <div style="float: left; padding-right: 3px;">
		<div style='display: none;' id="progress-${data.id}">
		    <img src="${h.url_for('/static/style/data_running.gif')}" border="0" align="middle" >
		</div>
		%if data_state == 'running':
		    <div><img src="${h.url_for('/static/style/data_running.gif')}" border="0" align="middle"></div>
		%elif data_state != 'ok':
		    <div><img src="${h.url_for( "/static/style/data_%s.png" % data_state )}" border="0" align="middle"></div>
		%endif
	    </div>			
            <%doc>
	    <div style="float: right;">
	    <a href="${h.url_for( controller='dataset', dataset_id=data.id, action='display', filename='index')}" target="galaxy_main"><img src="${h.url_for('/static/images/eye_icon.png')}" rollover="${h.url_for('/static/images/eye_icon_dark.png')}" width='16' height='16' alt='display data' title='display data' class='displayButton' border='0'></a>
	    <a href="${h.url_for( action='edit', id=data.id )}" target="galaxy_main"><img src="${h.url_for('/static/images/pencil_icon.png')}" rollover="${h.url_for('/static/images/pencil_icon_dark.png')}" width='16' height='16' alt='edit attributes' title='edit attributes' class='editButton' border='0'></a>
	    <a href="${h.url_for( action='delete', id=data.id )}" class="historyItemDelete" id="historyItemDelter-${data.id}"><img src="${h.url_for('/static/images/delete_icon.png')}" rollover="${h.url_for('/static/images/delete_icon_dark.png')}" width='16' height='16' alt='delete' class='deleteButton' border='0'></a>
	    </div>
            </%doc>
            <table cellspacing="0" cellpadding="0" border="0" width="100%"><tr>
	    <td width="*">
                <input type="checkbox" name="dataset_ids" value="${data.id}"/>
                <span class="historyItemTitle"><b>${data.display_name()}</b></span>
                <a id="dataset-${data.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                <div popupmenu="dataset-${data.id}-popup">
                    <a class="action-button" href="${h.url_for( action='dataset', id=data.id )}">Edit this dataset's attributes and permissions</a>
                    <a class="action-button" confirm="Are you sure you want to delete dataset '${data.name}'?" href="${h.url_for( action='dataset', delete=True, id=data.id )}">Remove this dataset</a>
                </div>
            </td>
            <td width="100">${data.ext}</td>
            <td width="50"><span class="${data.dbkey}">${data.dbkey}</span></td>
            <td width="200">${data.info}</td>
            </tr></table>
	</div>
        
        ## Body for history items, extra info and actions, data "peek"
        
        <div id="info${data.id}" class="historyItemBody">
            <div>
                ${data.blurb}
            </div>
            <div> 
                %if data.has_data:
                    <a href="${h.url_for( action='display', id=data.id, tofile='yes', toext='data.ext' )}" target="_blank">save</a>
                    %for display_app in data.datatype.get_display_types():
                        <% display_links = data.datatype.get_display_links( data, display_app, app, request.base ) %>
                        %if len( display_links ) > 0:
                            | ${data.datatype.get_display_label(display_app)}
                            %for display_name, display_link in display_links:
                                <a target="_blank" href="${display_link}">${display_name}</a> 
                            %endfor
                        %endif
                    %endfor
                %endif
            </div>
            %if data.peek != "no peek":
                <div><pre id="peek${data.id}" class="peek">${data.display_peek()}</pre></div>
            %endif
            ## Recurse for child datasets
            %if len( data.children ) > 0:
		## FIXME: This should not be in the template, there should
		##        be a 'visible_children' method on dataset.
                <%
		children = []
                for child in data.children:
                    if child.visible:
                        children.append( child )
                %>
                %if len( children ) > 0:
                    <div>
                        There are ${len( children )} secondary datasets.
                        %for idx, child in enumerate(children):
                            ${render_dataset( child, idx + 1 )}
                        %endfor
                    </div>
                %endif
            %endif
        </div>
    </div>
</%def>
