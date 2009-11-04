<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif
</br>
</br>
<h3>New address</h3>

<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', action='show_info', admin_view=admin_view, user_id=user.id)}">
        <span>Manage User Information</span></a>
    </li>
</ul>
<div class="toolForm">
<form name="login_info" id="login_info" action="${h.url_for( controller='user', action='new_address', admin_view=admin_view, user_id=user.id )}" method="post" >
    <div class="toolFormTitle">New address</div>
    <div class="toolFormBody">
        %for field in widgets:
            <div class="form-row">
                <label>${field[ 'label' ]}</label>
                ${field[ 'widget' ].get_html()}
            </div>
        %endfor
        <div class="form-row">
            <input type="submit" name="save_new_address_button" value="Save">
        </div>
    </div>
</form>
</div>