<%inherit file="/base.mako"/>

<%def name="render_component( component )">
  <%
    if isinstance( component, trans.app.model.LibraryFolder ):
        render = False
        # Check the folder's datasets to see what can be rendered
        for library_folder_dataset_assoc in component.datasets:
            if render:
                break
            dataset = trans.app.model.Dataset.get( library_folder_dataset_assoc.dataset_id )
            for group_dataset_assoc in dataset.groups:
                if group_dataset_assoc.group_id in group_ids:
                    render = True
                    break
        # Check the folder's sub-folders to see what can be rendered
        for library_folder in component.folders:
            render_component( library_folder )
        if render:
            return render_folder( component )
    elif isinstance( component, trans.app.model.LibraryFolderDatasetAssociation ):
        render = False
        dataset = trans.app.model.Dataset.get( component.dataset_id )
        for group_dataset_assoc in dataset.groups:
            if group_dataset_assoc.group_id in group_ids:
                render = True
                break
        if render:
            return render_dataset( component )
  %>
</%def>

## Render the dataset `data` as history item, using `hid` as the displayed id
<%def name="render_dataset( data )">
  <div>
    <input type="checkbox" name="import_ids" value="${data.id}">${data.name}
    <a href="${h.url_for( controller='root', 
                          action='edit', 
                          lid=data.id )}"><img src="${h.url_for('/static/images/pencil_icon.png')}" 
                                               rollover="${h.url_for('/static/images/pencil_icon_dark.png')}" 
                                               width='16' 
                                               height='16' 
                                               alt='view or edit attributes' 
                                               title='view or edit attributes' 
                                               class='editButton' 
                                               style='vertical-align: middle'
                                               border='0'></a>
  </div>
</%def>

## Render a folder
<%def name="render_folder( this_folder )">
  <div>
    Folder: ${this_folder.name}
    <%
      components = this_folder.active_components
      components = [ ( getattr( components[i], "order_id" ), i, components [i] ) for i in xrange( len( components ) ) ]
      components.sort()
      components = [ tup[-1] for tup in components ]
    %>
    <blockquote>
      %for component in components:
        ${render_component( component )}
      %endfor
    </blockquote>
  </div>
</%def>

<%def name="title()">View Library: ${library.name}</%def>
<div class="toolForm">
  <div class="toolFormTitle">Import from Library: ${library.name}</div>
  <div class="toolFormBody">
    <form name="view_library" action="${h.url_for( '/library/index' )}" method="post">
      ${render_folder( library.root_folder )}
      <div style="clear: both"></div>
      <input type="submit" class="primary-button" name="import_dataset" value="Import Datasets">
    </form>
  </div>
</div>
