<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/browse_library.mako" import="render_dataset" />
<%namespace file="/library/common/common.mako" import="render_actions_on_multiple_items" />
<%namespace file="/library/common/common.mako" import="render_compression_types_help" />
<%namespace file="/library/common/common.mako" import="common_javascripts" />

<%!
    def inherit(context):
        if context.get('use_panels'):
            return '/webapps/galaxy/base_panels.mako'
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

##
## Override methods from base.mako and base_panels.mako
##
<%def name="center_panel()">
   <div style="overflow: auto; height: 100%;">
       <div class="page-container" style="padding: 10px;">
           ${render_content()}
       </div>
   </div>
</%def>

## Render the grid's basic elements. Each of these elements can be subclassed.
<%def name="body()">
    ${render_content()}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("jstorage")}
    ${common_javascripts()}
</%def>

<%def name="render_searched_components()">
    <ul style="padding-left: 1em; list-style-type: disc;">
        <li>name</li>
        <li>info</li>
        <li>dbkey (genome build)</li>
        <li>message</li>
        %if trans.app.config.enable_lucene_library_search:
            <li>disk file content</li>
        %endif
    </ul>
    <br/>
</%def>

<%def name="render_content()">
    <%
        from galaxy import util
        from galaxy.web.controllers.library_common import branch_deleted
        from time import strftime
 
        class RowCounter( object ):
            def __init__( self ):
                self.count = 0
            def increment( self ):
                self.count += 1
            def __str__( self ):
                return str( self.count )
    %>
 
    <br/><br/>
    <ul class="manage-table-actions">
        <li>
            <a class="action-button" href="${h.url_for( controller=cntrller, action='browse_libraries' )}" target="galaxy_main">Browse data libraries</a></div>
        </li>
    </ul>

    <h2>Results for search on &ldquo;${search_term}&rdquo;</h2>
 
    %if message:
        ${render_msg( message, status )}
    %endif
 
    %if lddas:
        <p>The string "${search_term}" was found in at least one of the following information components of the displayed library datasets.</p>
        ${render_searched_components()}
        <form name="act_on_multiple_datasets" action="${h.url_for( controller='library_common', action='act_on_multiple_datasets', cntrller=cntrller, use_panels=use_panels, show_deleted=show_deleted )}" onSubmit="javascript:return checkForm();" method="post">
            <input type="hidden" name="search_term" value="${search_term}"/>
            <table cellspacing="0" cellpadding="0" border="0" width="100%" class="grid" id="library-grid">
                <thead>
                    <tr class="libraryTitle">
                        <th>
                            <input type="checkbox" id="checkAll" name=select_all_datasets_checkbox value="true" onclick='checkAllFields(1);'/><input type="hidden" name=select_all_datasets_checkbox value="true"/>
                            Name
                        </th>
                        <th>Message</th>
                        <th>Uploaded By</th>
                        <th>Date</th>
                        <th>File Size</th>
                    </tr>
                </thead>
                <%
                    tracked_datasets = {}
                    row_counter = RowCounter()
                    my_row = row_counter.count
                %>
                %for ldda in lddas:
                    <%
                        library_dataset = ldda.library_dataset
                        folder = library_dataset.folder
                        library = folder.parent_library
                    %>
                    ${render_dataset( cntrller, ldda, library_dataset, False, library, folder, 0, my_row, row_counter, tracked_datasets, show_deleted=False )}
                    <%
                        my_row = row_counter.count
                        row_counter.increment()
                    %>
                %endfor
                ${render_actions_on_multiple_items( actions_to_exclude=[ 'manage_permissions' ] )}
            </table>
        </form>
        ${render_compression_types_help( comptypes )}
    %elif status != 'error':
        <p>The string "${search_term}" was not found in any of the following information components for any library datasets that you can access.</p>
        ${render_searched_components()}
    %endif
</%def>
