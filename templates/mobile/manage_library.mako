<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/library/common/common.mako" import="render_template_info" />

<% roles = trans.get_current_user_roles() %>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if trans.app.security_agent.can_modify_library_item( roles, library ):
    <div class="toolForm">
        <div class="toolFormTitle">Change library name and description</div>
        <div class="toolFormBody">
            <form name="library" action="${h.url_for( controller='library_common', action='library_info', id=trans.security.encode_id( library.id ), cntrller='mobile' )}" method="post" >
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
            ${render_template_info( 'mobile', library, library.id, 'library' )}
        </div>
    </div>
%endif
%if trans.app.security_agent.can_manage_library_item( roles, library ):
    <%
        roles = trans.sa_session.query( trans.app.model.Role ) \
                                .filter( trans.app.model.Role.table.c.deleted==False ) \
                                .order_by( trans.app.model.Role.table.c.name )
    %>
    ${render_permission_form( library, library.name, h.url_for( controller='library_common', cntrller='mobile', action='library_permissions', id=trans.security.encode_id( library.id ) ), roles )}
%endif

%if widgets:
    ${render_template_info( 'mobile', library, trans.security.encode_id( library.id ), 'edit_library_information', widgets )}
%endif
