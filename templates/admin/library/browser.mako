<%inherit file="/base.mako"/>
<%namespace file="common.mako" import="render_dataset" />

<%def name="title()">Import from Library</%def>
<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <link href="${h.url_for('/static/style/library.css')}" rel="stylesheet" type="text/css" />
</%def>

<script type="text/javascript">
    //var q = jQuery.noConflict();
    $( document ).ready( function () {
        // Hide all the folder contents
        $("ul").filter("ul#subFolder").hide();
        // Handle the hide/show triangles
        $("li.libraryOrFolderRow").wrap( "<a href='#' class='expandLink'></a>" ).click( function() {
            var contents = $(this).parent().next("ul");
            if ( this.id == "libraryRow" ) {
                var icon_open = "${h.url_for( '/static/images/silk/book_open.png' )}";
                var icon_closed = "${h.url_for( '/static/images/silk/book.png' )}";
            } else {
                var icon_open = "${h.url_for( '/static/images/silk/folder_page.png' )}";
                var icon_closed = "${h.url_for( '/static/images/silk/folder.png' )}";
            }
            if ( contents.is(":visible") ) {
                contents.slideUp("fast");
                $(this).children().find("img.expanderIcon").each( function() { this.src = "${h.url_for( '/static/images/silk/resultset_next.png' )}"; });
                $(this).children().find("img.rowIcon").each( function() { this.src = icon_closed; });
            } else {
                contents.slideDown("fast");
                $(this).children().find("img.expanderIcon").each( function() { this.src = "${h.url_for( '/static/images/silk/resultset_bottom.png' )}"; });
                $(this).children().find("img.rowIcon").each( function() { this.src = icon_open; });
            }
        });
        // Hide all dataset bodies
        $("div.historyItemBody").hide();
        // Handle the dataset body hide/show link.
        $("div.historyItemWrapper").each( function() {
            var id = this.id;
            var li = $(this).parent();
            var body = $(this).children( "div.historyItemBody" );
            var peek = body.find( "pre.peek" )
            $(this).children( ".historyItemTitleBar" ).find( ".historyItemTitle" ).wrap( "<a href='#'></a>" ).click( function() {
                if ( body.is(":visible") ) {
                    if ( $.browser.mozilla ) { peek.css( "overflow", "hidden" ) }
                    body.slideUp( "fast" );
                    li.removeClass( "datasetHighlighted" );
                } 
                else {
                    body.slideDown( "fast", function() { 
                        if ( $.browser.mozilla ) { peek.css( "overflow", "auto" ); } 
                    });
                    li.addClass( "datasetHighlighted" );
                }
                return false;
            });
        });
    });
    function checkForm() {
        if ( $("select#with-selected-select option:selected").text() == "delete" ) {
            if ( confirm( "Are you sure you want to delete these datasets?" ) ) {
                return true;
            } else {
                return false;
            }
        }
    }
</script>

<%def name="render_folder( parent, parent_pad )">
  <%
    ##if not trans.app.security_agent.check_folder_contents( trans.user, parent ):
    ##  return ""
    pad = parent_pad + 20
    if parent_pad == 0:
        expander = "/static/images/silk/resultset_bottom.png"
        folder = "/static/images/silk/folder_page.png"
        subfolder = False
    else:
        expander = "/static/images/silk/resultset_next.png"
        folder = "/static/images/silk/folder.png"
        subfolder = True
  %>
  <li class="folderRow libraryOrFolderRow" style="padding-left: ${pad}px;">
    <div class="rowTitle">
      <img src="${h.url_for( expander )}" class="expanderIcon"/><img src="${h.url_for( folder )}" class="rowIcon"/>
      ${parent.name}
      %if parent.description:
        <i>- ${parent.description}</i>
      %endif
      <a id="folder-${parent.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
    </div>
    <div popupmenu="folder-${parent.id}-popup">
      <a class="action-button" href="${h.url_for( action='dataset', folder_id=parent.id )}">Add new dataset to this folder</a>
      <a class="action-button" href="${h.url_for( action='folder', new=True, id=parent.id )}">Create a new subfolder in this folder</a>
      <a class="action-button" href="${h.url_for( action='folder', rename=True, id=parent.id )}">Rename this folder</a>
      %if subfolder:
      <a class="action-button" confirm="Are you sure you want to delete folder '${parent.name}'?" href="${h.url_for( action='folder', delete=True, id=parent.id )}">Remove this folder and its contents</a>
      %endif
    </div>
  </li>
  %if subfolder:
    <ul id="subFolder">
  %else:
    <ul>
  %endif
      %for folder in parent.active_folders:
        ${render_folder( folder, pad )}
      %endfor
      %for dataset in parent.active_datasets:
        ##%if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_ACCESS, dataset=dataset.dataset ):
            <li class="datasetRow" style="padding-left: ${pad + 18}px;">${render_dataset( dataset )}</li>
        ##%endif
      %endfor
    </ul>
</%def>

<h2>Libraries</h2>

%if message:
<%
    try:
        messagetype
    except:
        messagetype = "done"
%>
<p />
<div class="${messagetype}message">
    ${message}
</div>
<p />
%endif

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( action='library', new=True )}">
            <img src="${h.url_for( '/static/images/silk/add.png' )}" />
            <span>Create a new library</span>
        </a>
    </li>
</ul>
<form name="update_multiple_datasets" action="${h.url_for( action='datasets' )}" onSubmit="javascript:return checkForm();" method="post">
<ul>
%if libraries:
%for library in libraries:
  ##%if trans.app.security_agent.check_folder_contents( trans.user, library ):
  <li class="libraryRow libraryOrFolderRow" id="libraryRow"><div class="rowTitle"><table cellspacing="0" cellpadding="0" border="0" width="100%" class="libraryTitle"><tr>
    <th width="*">
        <img src="${h.url_for( '/static/images/silk/resultset_bottom.png' )}" class="expanderIcon"/><img src="${h.url_for( '/static/images/silk/book_open.png' )}" class="rowIcon"/>
        ${library.name}
        %if library.description:
          <i>- ${library.description}</i>
        %endif
        <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="library-${library.id}-popup">
            <a class="action-button" href="${h.url_for( action='library', rename=True, id=library.id )}">Rename this library</a>
            <a class="action-button" confirm="Are you sure you want to delete library '${library.name}'?" href="${h.url_for( action='library', delete=True, id=library.id )}">Remove this library and its contents</a>
        </div>
    </th>
    <th width="100">Format</th>
    <th width="50">Db</th>
    <th width="200">Info</th>
  </tr></table></div></li>
    <ul>
      ${render_folder( library.root_folder, 0 )}
    </ul>
  <br/>
  ##%endif
%endfor
</ul>
<div style="float: right;">
    With selected datasets:
    <select name="action" id="with-selected-select">
        <option value="None" selected></option>
        <option value="edit">edit permissions</option>
        <option value="delete">delete</option>
    </select>
    <input type="submit" class="primary-button" name="with-selected" id="with-selected-submit" value="go"/>
</div>
</form>
%else:
There are no libraries.
%endif
