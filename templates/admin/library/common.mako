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
    ##%if not trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset = data.dataset ):
    ##    <div class="historyItemWrapper historyItem historyItem-${data_state} historyItem-noPermission" id="historyItem-${data.id}">
    ##%else:
        <div class="historyItemWrapper historyItem historyItem-${data_state}" id="historyItem-${data.id}">
    ##%endif
        
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
