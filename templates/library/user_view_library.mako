<%inherit file="/base.mako"/>

<%def name="render_component( component )">
    <%
    if isinstance( component, trans.app.model.LibraryFolder ):
        return render_folder( component )
    elif isinstance( component, trans.app.model.LibraryFolderDatasetAssociation ):
        return render_dataset( component )
    %>
</%def>


## Render the dataset `data` as history item, using `hid` as the displayed id
<%def name="render_dataset( data )">
    <div>
    <input type="checkbox" name="import_ids" value="${data.id}">${data.name}
    <div>
</%def>

## Render a folder
<%def name="render_folder( this_folder )">

  <div>
  Folder: ${this_folder.name}
        <%
        components = list( this_folder.folders ) + list( this_folder.datasets )
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
    <form name="view_library" action="${h.url_for( 'index' )}" method="post">
      ${render_folder( library.root_folder )}
      
      <div style="clear: both"></div>
      <input type="submit" class="primary-button" name="import_dataset" value="Import Datasets">
    </form>

  </div>
</div>
  
