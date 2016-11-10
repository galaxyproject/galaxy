<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <form name="change_communication" id="change_communication" action="${h.url_for( controller='user', action='change_communication', cntrller=cntrller )}" method="post" >
        <div class="toolFormTitle">Change your communication settings</div>
        <div class="form-row">
            <label>Activate real-time communication with other Galaxy users.</label>
            <input type="checkbox" name="enable_communication_server" ${activated} />
        </div>
        <div class="form-row">
            <input type="submit" name="change_communication_button" value="Save"/>
        </div>
    </form>
</div>
