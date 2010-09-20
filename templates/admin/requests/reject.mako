<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<h2>Reject Sequencing Request "${request.name}"</h2>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='list', operation='events', id=trans.security.encode_id(request.id) )}">
        <span>Events</span></a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='list', operation='show', id=trans.security.encode_id(request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Reject request</div>
        <form name="event" action="${h.url_for( controller='requests_admin', action='reject', id=trans.security.encode_id(request.id))}" method="post" >
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