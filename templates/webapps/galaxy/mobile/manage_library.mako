<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/dataset/security_common.mako" import="render_permission_form" />
<%namespace file="/common/template_common.mako" import="render_template_fields" />

<% current_user_roles = trans.get_current_user_roles() %>

%if message:
    ${render_msg( message, status )}
%endif

%if trans.app.security_agent.can_modify_library_item( current_user_roles, library ):
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
                <div class="form-row">
                    <label>Synopsis:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="synopsis" value="${library.synopsis}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <input type="submit" name="library_info_button" value="Save"/>
            </form>
        </div>
    </div>
    <p/>
%else:
    <div class="toolForm">
        <div class="toolFormTitle">View information about ${library.name}</div>
        <div class="form-row">
            <label>Name:</label>
            ${library.name}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Description:</label>
            ${library.description}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Synopsis:</label>
            ${library.synopsis}
        </div>
        <div style="clear: both"></div>
        <div class="toolForm">
            ${render_template_fields( cntrller='mobile', item_type='library', widgets=widgets, widget_fields_have_contents=widget_fields_have_contents, library_id=trans.security.encode_id( library.id ), info_association=info_association, inherited=inherited )}
        </div>
    </div>
%endif
%if trans.app.security_agent.can_manage_library_item( current_user_roles, library ):
    <% roles = trans.app.security_agent.get_legitimate_roles( trans, library, 'mobile' ) %>
    ${render_permission_form( library, library.name, h.url_for( controller='library_common', cntrller='mobile', action='library_permissions', id=trans.security.encode_id( library.id ) ), roles )}
%endif

%if widgets:
    ${render_template_fields( cntrller='mobile', item_type='library', widgets=widgets, widget_fields_have_contents=widget_fields_have_contents, library_id=trans.security.encode_id( library.id ), info_association=info_association, inherited=inherited )}
%endif
