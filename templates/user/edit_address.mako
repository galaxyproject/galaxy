<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif
</br>
</br>
<h3>Edit address</h3>

<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', action='manage_user_info', cntrller=cntrller, user_id=trans.security.encode_id( user.id) )}">Manage user information</a>
    </li>
</ul>
<div class="toolForm">
    <div class="toolFormTitle">Edit address</div>
    <div class="toolFormBody">
        <form name="login_info" id="login_info" action="${h.url_for( controller='user', action='edit_address', cntrller=cntrller, address_id=trans.security.encode_id( address_obj.id ), user_id=trans.security.encode_id( user.id ) )}" method="post" >
            <div class="form-row">
                <label>Short Description:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="short_desc" value="${address_obj.desc}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="name" value="${address_obj.name}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Institution:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="institution" value="${address_obj.institution}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Address:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="address" value="${address_obj.address}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>City:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="city" value="${address_obj.city}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>State/Province/Region:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="state" value="${address_obj.state}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Postal Code:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="postal_code" value="${address_obj.postal_code}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Country:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="country" value="${address_obj.country}" size="40">
                </div>
                <div class="toolParamHelp" style="clear: both;">Required</div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Phone:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="text" name="phone" value="${address_obj.phone}" size="40">
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="edit_address_button" value="Save changes">
            </div>
        </form>
    </div>
</div>
