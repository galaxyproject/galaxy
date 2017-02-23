<%inherit file="/base.mako"/>
<%namespace file="/user/info.mako" import="render_user_info" />
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

${render_user_info()}

%if user.values or user_info_forms:
    <p></p>
    <div class="toolForm">
        <form name="user_info" id="user_info" action="${h.url_for( controller='user', action='edit_info', cntrller=cntrller, user_id=trans.security.encode_id( user.id ) )}" method="post" >
            <div class="toolFormTitle">User information</div>
            %if user_type_fd_id_select_field and len( user_type_fd_id_select_field.options ) >= 1:
                <div class="form-row">
                    <label>User type:</label>
                    ${user_type_fd_id_select_field.get_html()}
                </div>
            %else:
                <input type="hidden" name="user_type_fd_id" value="${trans.security.encode_id( user_type_fd_id )}"/>
            %endif
            %for field in widgets:
                <div class="form-row">
                    <label>${field['label']}:</label>
                    ${field['widget'].get_html()}
                    <div class="toolParamHelp" style="clear: both;">
                        ${field['helptext']}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor
            <div class="form-row">
                <input type="submit" name="edit_user_info_button" value="Save"/>
            </div>
        </form>
    </div>
    <p></p>
%endif
