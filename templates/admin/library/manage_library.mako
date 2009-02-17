<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/admin/library/common.mako" import="render_available_templates" />
<%namespace file="/admin/library/common.mako" import="render_existing_library_item_info" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Change library name and description</div>
    <div class="toolFormBody">
        <form name="library" action="${h.url_for( controller='admin', action='library', manage=True )}" method="post" >
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
            <div class="form-row">
                <label>Also change the root folder's name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="checkbox" name="root_folder"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="id" value="${library.id}"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <input type="submit" name="rename_library_button" value="Save"/>
        </form>
    </div>
</div>

<p/>
<%
    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all()
%>

${render_permission_form( library, library.name, h.url_for( conroller='admin', action='library', id=library.id ), roles )}

${render_existing_library_item_info( library )}

${render_available_templates( library )}
