<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif
<br/>
<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='requests', action='list')}">
        <span>Browse requests</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Add a new request</div>
    %if not request_types:
        There are no request types created for a new request.
    %else:
        <div class="toolFormBody">
            <form name="select_request_type" action="${h.url_for( controller='requests', action='new', create=True )}" method="post" >
                <div class="form-row">
                    <label>
                        Select Request Type:
                    </label>
                    <select name="request_type_id">
                        %for rt in request_types:
                            <option value="${rt.id}">${rt.name}</option>
                        %endfor
                    </select>
                    <input type="submit" name="create_request" value="Go"/>
                </div>
            </form>
        </div>
    %endif
</div>
