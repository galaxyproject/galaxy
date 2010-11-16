<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif
<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request_history', cntrller=cntrller, id=trans.security.encode_id(request.id) )}">View history</a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id(request.id) )}">Browse this request</a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Reject sequencing request "${request.name}"</div>
        <form name="event" action="${h.url_for( controller='requests_admin', action='reject_request', id=trans.security.encode_id( request.id ) )}" method="post" >
            <div class="form-row">
                Rejecting this request will move the request state to <b>Rejected</b>.
            </div>
            <div class="form-row">
                <label>Comments</label>
                <textarea name="comment" rows="5" cols="40"></textarea>
                <div class="toolParamHelp" style="clear: both;">
                    Required
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="reject_button" value="Reject"/>
                <input type="submit" name="cancel_reject_button" value="Cancel"/>
            </div>
        </form>
    </div>
</div>
