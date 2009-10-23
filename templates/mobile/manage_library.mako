<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/library/common.mako" import="render_template_info" />

<% user, roles = trans.get_user_and_roles() %>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.can_modify_library_item( user, roles, library ):
    <div class="toolForm">
        <div class="toolFormTitle">Change library name and description</div>
        <div class="toolFormBody">
            <form name="library" action="${h.url_for( controller='library', action='library', rename=True )}" method="post" >
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
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="hidden" name="obj_id" value="${library.id}"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <input type="submit" name="rename_library_button" value="Save"/>
            </form>
        </div>
    </div>
    <p/>
%else:
    <div class="toolForm">
        <div class="toolFormTitle">View information about ${library.name}</div>
        <div class="toolFormBody">
            <div class="form-row">
                <b>Name:</b> ${library.name}
                <div style="clear: both"></div>
                <b>Info:</b> ${library.description}
                <div style="clear: both"></div>
            </div>
        </div>
        <div class="toolForm">
            ${render_template_info( library, library.id, 'library' )}
        </div>
    </div>
%endif
%if trans.app.security_agent.can_manage_library_item( user, roles, library ):
    <%
        roles = trans.sa_session.query( trans.app.model.Role ) \
                                .filter( trans.app.model.Role.table.c.deleted==False ) \
                                .order_by( trans.app.model.Role.table.c.name )
    %>
    ${render_permission_form( library, library.name, h.url_for( controller='library', action='library', id=library.id, permissions=True ), roles )}
%endif

%if widgets:
    ${render_template_info( library, library_id, 'library', widgets )}
%endif
