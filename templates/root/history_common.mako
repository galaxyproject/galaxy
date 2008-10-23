## Render the dataset `data` as history item, using `hid` as the displayed id
<%def name="render_dataset( data, hid, show_deleted_on_refresh = False )">
    <%
	if data.state in ['no state','',None]:
	    data_state = "queued"
	else:
	    data_state = data.state
    %>
    <div class="historyItemWrapper historyItem historyItem-${data_state}" id="historyItem-${data.id}">
        
    %if data.deleted:
        <div class="warningmessagesmall">
            <strong>This dataset has been deleted. Click <a href="${h.url_for( controller='dataset', action='undelete', id=data.id )}" class="historyItemUndelete" id="historyItemUndeleter-${data.id}" target="galaxy_history">here</a> to undelete.</strong>
        </div>
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
	    <div style="float: right;">
	    <a href="${h.url_for( controller='dataset', dataset_id=data.id, action='display', filename='index')}" target="galaxy_main"><img src="${h.url_for('/static/images/eye_icon.png')}" rollover="${h.url_for('/static/images/eye_icon_dark.png')}" width='16' height='16' alt='display data' title='display data' class='displayButton' border='0'></a>
	    <a href="${h.url_for( action='edit', id=data.id )}" target="galaxy_main"><img src="${h.url_for('/static/images/pencil_icon.png')}" rollover="${h.url_for('/static/images/pencil_icon_dark.png')}" width='16' height='16' alt='edit attributes' title='edit attributes' class='editButton' border='0'></a>
	    <a href="${h.url_for( action='delete', id=data.id, show_deleted_on_refresh=show_deleted_on_refresh )}" class="historyItemDelete" id="historyItemDeleter-${data.id}"><img src="${h.url_for('/static/images/delete_icon.png')}" rollover="${h.url_for('/static/images/delete_icon_dark.png')}" width='16' height='16' alt='delete' class='deleteButton' border='0'></a>
	    </div>
	    <span class="historyItemTitle"><b>${hid}: ${data.display_name()}</b></span>
	</div>
        
        ## Body for history items, extra info and actions, data "peek"
        
        <div id="info${data.id}" class="historyItemBody">
            %if data_state == "queued":
                <div>Job is waiting to run</div>
            %elif data_state == "running":
                <div>Job is currently running</div>
            %elif data_state == "error":
                <div>
                    An error occurred running this job: <i>${data.display_info().strip()}</i>, 
                    <a href="${h.url_for( controller='dataset', action='errors', id=data.id )}" target="galaxy_main">report this error</a>
                </div>
            %elif data_state == "discarded":
                <div>
                    The job creating this dataset was cancelled before completion.
                </div>
            %elif data_state == "empty":
                <div>No data: <i>${data.display_info()}</i></div>
            %elif data_state == "ok":
                <div>
                    ${data.blurb},
                    format: <span class="${data.ext}">${data.ext}</span>, 
                    database:
                    %if data.dbkey == '?':
                        <a href="${h.url_for( action='edit', id=data.id )}" target="galaxy_main">${data.dbkey}</a>
                    %else:
                        <span class="${data.dbkey}">${data.dbkey}</span>
                    %endif
                </div>
                <div class="info">Info: ${data.display_info()} </div>
                <div> 
                    %if data.has_data:
                        <a href="${h.url_for( action='display', id=data.id, tofile='yes', toext=data.ext )}" target="_blank">save</a>
                        %for display_app in data.datatype.get_display_types():
                            <% display_links = data.datatype.get_display_links( data, display_app, app, request.base + h.url_for() ) %>
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
	    %else:
		<div>Error: unknown dataset state "${data_state}".</div>
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
