<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif
</br>
</br>
<h3>Edit address</h3>

<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', action='show_info')}">
        <span>Manage User Information</span></a>
    </li>
</ul>
<div class="toolForm">
<form name="login_info" id="login_info" action="${h.url_for( controller='user', action='edit_address', admin_view=admin_view, address_id=address.id, user_id=user.id )}" method="post" >
    <div class="toolFormTitle">Edit address</div>
    <div class="toolFormBody">
        %for field in widgets:
            <div class="form-row">
                <label>${field[ 'label' ]}</label>
                ${field[ 'widget' ].get_html()}
            </div>
        %endfor
        <div class="form-row">
            <input type="submit" name="edit_address_button" value="Save changes">
        </div>
    </div>
</form>
</div>