<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/library/common.mako" import="render_available_templates" />
<%namespace file="/admin/library/common.mako" import="render_existing_library_item_info" />

<% available_templates = library.get_library_item_info_templates( template_list=[], restrict=False ) %>
%if available_templates:
    <b>Add information to this library using available templates</b>
    <a id="library-${library.id}--popup" class="popup-arrow" style="display: none;">&#9660;</a>
    <div popupmenu="library-${library.id}--popup">
        <a class="action-button" href="${h.url_for( controller='admin', action='library', id=library.id, information=True, restrict=False, render_templates=True )}">Show templates</a>
        <a class="action-button" href="${h.url_for( controller='admin', action='library', id=library.id, information=True, restrict=False, render_templates=False )}">Hide templates</a>
    </div>
%endif
<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='admin', action='browse_library', id=library.id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if render_templates not in [ 'False', False ]:
    ${render_available_templates( library, library.id, restrict=False )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Change library name and description</div>
    <div class="toolFormBody">
        <form name="library" action="${h.url_for( controller='admin', action='library', information=True, id=library.id )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${library.name}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="description" value="${library.description}" size="40"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="rename_library_button" value="Save"/>
        </form>
    </div>
</div>

<%
    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
    library.refresh()
%>

<% library.refresh() %>
${render_existing_library_item_info( library, library.id )}
