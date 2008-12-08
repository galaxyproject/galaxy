<%doc>
    Shamelessly stolen from history... this needs to be cleaned up to remove a
    bunch of stuff that doesn't apply to library datasets (like state, etc).
</%doc>

## Render the dataset `data`
<%def name="render_dataset( data, selected, deleted )">
    <div class="historyItemWrapper historyItem historyItem-${data.state}" id="historyItem-${data.id}">
        
    ## Header row for library items (name, state, action buttons)
	<div style="overflow: hidden;" class="historyItemTitleBar">		
        <table cellspacing="0" cellpadding="0" border="0" width="100%">
            <tr>
                <td width="*">
                    %if selected:
                        <input type="checkbox" name="dataset_ids" value="${data.id}" checked/>
                    %else:
                        <input type="checkbox" name="dataset_ids" value="${data.id}"/>
                    %endif
                    <span class="historyItemTitle"><b>${data.display_name()}</b></span>
                    %if not deleted:
                        <a id="dataset-${data.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="dataset-${data.id}-popup">
                            <a class="action-button" href="${h.url_for( controller='admin', action='dataset', id=data.id )}">Edit this dataset's attributes and permissions</a>
                            %if data.has_data:
                                <a class="action-button" href="${h.url_for( controller='admin', action='download_dataset_from_folder', id=data.id )}">Download this dataset</a>
                            %endif
                            <a class="action-button" confirm="Click OK to remove dataset '${data.name}'?" href="${h.url_for( controller='admin', action='dataset', delete=True, id=data.id )}">Remove this dataset from the library</a>
                        </div>
                    %endif
                </td>
                <td width="100">${data.ext}</td>
                <td width="50"><span class="${data.dbkey}">${data.dbkey}</span></td>
                <td width="200">${data.info}</td>
            </tr>
        </table>
    </div>
        
    ## Body for library items, extra info and actions, data "peek"
    <div id="info${data.id}" class="historyItemBody">
        <div>${data.blurb}</div>
        <div> 
            %if data.has_data:
                %for display_app in data.datatype.get_display_types():
                    <% display_links = data.datatype.get_display_links( data, display_app, app, request.base ) %>
                    %if len( display_links ) > 0:
                        ${data.datatype.get_display_label(display_app)}
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
        %if len( data.visible_children ) > 0:
            <div>
                There are ${len( data.visible_children )} secondary datasets.
                %for idx, child in enumerate( data.visible_children ):
                    ${ render_dataset( child, selected, deleted ) }
                %endfor
            </div>
        %endif
    </div>
</%def>
