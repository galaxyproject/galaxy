<% _=n_ %>
## Render the dataset `data` as history item, using `hid` as the displayed id
<%def name="render_dataset( data, hid, show_deleted_on_refresh = False )">
    <%
    	if data.state in ['no state','',None]:
    	    data_state = "queued"
    	else:
    	    data_state = data.state
    	user, roles = trans.get_user_and_roles()
    %>
    %if not trans.app.security_agent.allow_action( user, roles, data.permitted_actions.DATASET_ACCESS, dataset = data.dataset ):
        <div class="historyItemWrapper historyItem historyItem-${data_state} historyItem-noPermission" id="historyItem-${data.id}">
    %else:
        <div class="historyItemWrapper historyItem historyItem-${data_state}" id="historyItem-${data.id}">
    %endif
        
    %if data.deleted:
        <div class="warningmessagesmall">
            <strong>This dataset has been deleted. Click <a href="${h.url_for( controller='dataset', action='undelete', id=data.id )}" class="historyItemUndelete" id="historyItemUndeleter-${data.id}" target="galaxy_history">here</a> to undelete.</strong>
        </div>
    %endif
    
        ## Header row for history items (name, state, action buttons)
	<div style="overflow: hidden;" class="historyItemTitleBar">		
	    <div class="historyItemButtons">
            %if data_state == "upload":
		## TODO: Make these CSS, just adding a "disabled" class to the normal
		## links should be enough. However the number of datasets being uploaded
		## at a time is usually small so the impact of these images is also small.
	        <img src="${h.url_for('/static/images/eye_icon_grey.png')}" width='16' height='16' alt='display data' title='display data' class='button display' border='0'>
	        <img src="${h.url_for('/static/images/pencil_icon_grey.png')}" width='16' height='16' alt='edit attributes' title='edit attributes' class='button edit' border='0'>
            %else:
	        <a class="icon-button display" title="display data" href="${h.url_for( controller='dataset', dataset_id=data.id, action='display', filename='index')}" target="galaxy_main"></a>
	        <a class="icon-button edit" title="edit attributes" href="${h.url_for( controller='root', action='edit', id=data.id )}" target="galaxy_main"></a>
            %endif
	    <a class="icon-button delete" title="delete" href="${h.url_for( action='delete', id=data.id, show_deleted_on_refresh=show_deleted_on_refresh )}" id="historyItemDeleter-${data.id}"></a>
	    </div>
	    <span class="state-icon"></span>
	    <span class="historyItemTitle"><b>${hid}: ${data.display_name().decode('utf-8')}</b></span>
	</div>
        
        ## Body for history items, extra info and actions, data "peek"
        
        <div id="info${data.id}" class="historyItemBody">
            %if not trans.app.security_agent.allow_action( user, roles, data.permitted_actions.DATASET_ACCESS, dataset = data.dataset ):
                <div>You do not have permission to view this dataset.</div>
            %elif data_state == "upload":
                <div>Dataset is uploading</div>
            %elif data_state == "queued":
                <div>${_('Job is waiting to run')}</div>
            %elif data_state == "running":
                <div>${_('Job is currently running')}</div>
            %elif data_state == "error":
                <div>
                    An error occurred running this job: <i>${data.display_info().strip()}</i>
                </div>
		<div>
		    <a href="${h.url_for( controller='dataset', action='errors', id=data.id )}" target="galaxy_main">report this error</a>
		    | <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main">rerun</a>
		</div>
            %elif data_state == "discarded":
                <div>
                    The job creating this dataset was cancelled before completion.
                </div>
            %elif data_state == 'setting_metadata':
                <div>${_('Metadata is being Auto-Detected.')}</div>
            %elif data_state == "empty":
                <div>${_('No data: ')}<i>${data.display_info()}</i></div>
            %elif data_state == "ok":
                <div>
                    ${data.blurb},
                    format: <span class="${data.ext}">${data.ext}</span>, 
                    database:
                    %if data.dbkey == '?':
                        <a href="${h.url_for( controller='root', action='edit', id=data.id )}" target="galaxy_main">${_(data.dbkey)}</a>
                    %else:
                        <span class="${data.dbkey}">${_(data.dbkey)}</span>
                    %endif
                </div>
                <div class="info">${_('Info: ')}${data.display_info()}</div>
                <div> 
                    %if data.has_data:
                        <a href="${h.url_for( action='display', id=data.id, tofile='yes', toext=data.ext )}" target="_blank">save</a>
			| <a href="${h.url_for( controller='tool_runner', action='rerun', id=data.id )}" target="galaxy_main">rerun</a>
                        %for display_app in data.datatype.get_display_types():
                            <% display_links = data.datatype.get_display_links( data, display_app, app, request.base ) %>
                            %if len( display_links ) > 0:
                                | ${data.datatype.get_display_label(display_app)}
				%for display_name, display_link in display_links:
				    <a target="_blank" href="${display_link}">${_(display_name)}</a> 
				%endfor
                            %endif
                        %endfor
                    %endif
                </div>
                %if data.peek != "no peek":
                    <div><pre id="peek${data.id}" class="peek">${_(data.display_peek())}</pre></div>
                %endif
	    %else:
		<div>${_('Error: unknown dataset state "%s".') % data_state}</div>
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
                            ${render_dataset( child, idx + 1, show_deleted_on_refresh = show_deleted_on_refresh )}
                        %endfor
                    </div>
                %endif
            %endif

        </div>
    </div>

</%def>
