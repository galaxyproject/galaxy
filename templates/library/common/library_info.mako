<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/common.mako" import="render_template_info" />

<%
    if not trans.user_is_admin():
        user, roles = trans.get_user_and_roles()
%>

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ) )}"><span>Browse this data library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if cntrller == 'library_admin' or trans.app.security_agent.can_modify_library_item( user, roles, library ):
    <div class="toolForm">
        <div class="toolFormTitle">Change library name and description</div>
        <div class="toolFormBody">
            <form name="library" action="${h.url_for( controller='library_common', action='library_info', id=trans.security.encode_id( library.id ), cntrller=cntrller )}" method="post" >
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
                <b>Description:</b> ${library.description}
                <div style="clear: both"></div>
            </div>
        </div>
    </div>
%endif

%if widgets:
    ${render_template_info( cntrller, library, trans.security.encode_id( library.id ), 'library_info', widgets )}
%endif
