<%inherit file="/base.mako"/>

<%def name="render_component( component )">
  <%
    if isinstance( component, trans.app.model.LibraryFolder ):
      return render_folder( component )
    elif isinstance( component, trans.app.model.LibraryFolderDatasetAssociation ) and not component.deleted:
      return render_dataset( component )
  %>
</%def>

## Render the dataset `data` as folder item, using `hid` as the displayed id
<%def name="render_dataset( data )">
  <%
    if data.state in ['no state','',None]:
      data_state = "queued"
    else:
      data_state = data.state
  %>
  <div class="toolForm">
    <div class="toolFormTitle">${data.display_name()}</div>
    <div class="toolFormBody">
      <div class="form-row">        
        ## Header row for folder items (name, state, action buttons)      
        <div style="overflow: hidden;" class="historyItemTitleBar">
          %if data_state != 'ok':
            <div><img src="${h.url_for( "/static/style/data_%s.png" % data_state )}" border="0" align="middle"></div>
          %endif
        </div>            
        <div style="float: right;">
          <a href="${h.url_for( controller='admin', 
                                action='dataset', 
                                id=data.id )}"><img src="${h.url_for('/static/images/pencil_icon.png')}" 
                                                    rollover="${h.url_for('/static/images/pencil_icon_dark.png')}" 
                                                    width='16' 
                                                    height='16' 
                                                    alt='edit attributes' 
                                                    title='edit attributes' 
                                                    class='editButton' 
                                                    border='0'></a>
          <a href="${h.url_for( controller='admin',
                                action='delete_dataset',
                                id=data.id )}"<img src="${h.url_for('/static/images/delete_icon.png')}" 
                                                           rollover="${h.url_for('/static/images/delete_icon_dark.png')}" 
                                                           width='16' 
                                                           height='16' 
                                                           alt='delete' 
                                                           class='deleteButton' 
                                                           border='0'></a>
        </div>
        ##<span class="historyItemTitle"><b>${data.display_name()}</b></span>
      </div>    
      ## Body for folder items, extra info and actions, data "peek"    
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
        %elif data_state == "empty":
          <div>No data: <i>${data.display_info()}</i></div>
        %elif data_state == "ok":
          <div>
            ${data.blurb},
            format: <span class="${data.ext}">${data.ext}</span>, 
            database:
            %if data.dbkey == '?':
              <a href="${h.url_for( controller='admin', action='dataset', id=data.id )}">${data.dbkey}</a>
            %else:
              <span class="${data.dbkey}">${data.dbkey}</span>
            %endif
          </div>
          <div class="info">Info: ${data.display_info()} </div>
            %if data.peek != "no peek":
              <div><pre id="peek${data.id}">${data.display_peek()}</pre></div>
            %endif
        %else:
          <div>Error: unknown dataset state "${data_state}".</div>
        %endif         
        ## Recurse for child datasets
      </div>
    </div>
  </div>
</%def>

## Render a folder
<%def name="render_folder( this_folder )">
  <div class="toolForm">
    <div class="toolFormTitle">Contents of Folder: ${this_folder.name}</div>
    <div class="toolFormBody">
      <div class="form-row">
        <%
          components = list( this_folder.folders ) + list( this_folder.datasets )
          components = [ ( getattr( components[i], "order_id" ), i, components [i] ) for i in xrange( len( components ) ) ]
          components.sort()
          components = [ tup[-1] for tup in components ]
        %>
        %for component in components:
          ${render_component( component )}
        %endfor
      </div>
      <div style="clear: both"></div>
      <div class="form-row">
        <a href="${h.url_for( controller='admin', action='dataset', folder_id=this_folder.id )}">Add new dataset to folder '${this_folder.name}'</a>
        <div style="clear: both"></div>
        <a href="${h.url_for( controller='admin', action='folder', parent_id=this_folder.id )}">Add new folder to folder '${this_folder.name}'</a>
      </div>
      <div style="clear: both"></div>  
    </div>
  </div>
</%def>
<%def name="title()">Manage Folder: ${folder.name}</%def>
<div class="toolForm">
  <div class="form-row">
    <a href="${h.url_for( controller='admin', action='libraries' )}">Libraries</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="${h.url_for( controller='admin', action='groups' )}">Groups</a>&nbsp;&nbsp;|&nbsp;&nbsp;
    <tr><td><a href="${h.url_for( controller='admin', action='users' )}">Users</a></td></tr>
  </div>
  <div class="toolFormTitle">Change Folder Attributes</div>
  <div class="toolFormBody">
    <form name="rename_folder" action="folder" method="post" >        
      <div class="form-row">
        <label>Name:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <input type="text" name="name" value="${folder.name}" size="40">
        </div>
        <div style="clear: both"></div>
      </div>    
      <div class="form-row">
        <label>Description:</label>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <input type="text" name="description" value="${folder.description}" size="40">
        </div>
        <div style="clear: both"></div>
      </div>
      <div class="form-row">
        <div style="float: left; width: 250px; margin-right: 10px;">
          <input type="hidden" name="rename_folder" value="rename_folder">
        </div>
        <div style="float: left; width: 250px; margin-right: 10px;">
          <input type="hidden" name="id" value="${folder.id}">
        </div>
      </div>
      <input type="submit" value="Save">
    </form>
  </div>
</div>
<div style="clear: both"></div>
<div class="toolForm">
  <div class="toolFormTitle">Manage Folder Contents: ${folder.name}</div>
  <div class="toolFormBody">
    <div class="form-row">
    %if folder.parent:
      <a href="${h.url_for( controller='admin', action='folder', id=folder.parent_id )}">Up a Level</a>
    %elif folder.library_root:
      <a href="${h.url_for( controller='admin', action='library', id=folder.library_root[0].id )}">Manage Library</a>
    %endif
  </div>
  <div style="clear: both"></div>
    <div class="form-row">
      ${render_folder( folder )}
    </div>
    <div style="clear: both"></div>
  </div>
</div>
