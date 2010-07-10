<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Events for Sample ${sample.name}</%def>

<h2>Events for Sample "${sample.name}"</h2>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller=cntrller, action='list', operation='show', id=trans.security.encode_id(sample.request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>
<h3>User: ${sample.request.user.email}</h3>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <table class="grid">
        <thead>
            <tr>
                <th>State</th>
                <th>Description</th>
                <th>Last Update</th>
                <th>Comments</th>
            </tr>
        </thead>
        <tbody>
            %for state, desc, updated, comments in events_list:    
                <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                    <td><b><a>${state}</a></b></td>
                    <td><a>${desc}</a></td>
                    <td><a>${updated}</a></td>
                    <td><a>${comments}</a></td>
                </tr>             
            %endfor
        </tbody>
    </table>
</div>
%if cntrller == 'requests_admin' and trans.user_is_admin():
    <div class="toolForm">
        <div class="toolFormTitle">Change current state</div>
        <div class="toolFormBody">
            <form name="event" action="${h.url_for( controller='requests_admin', action='save_state', new=True, sample_id=sample.id)}" method="post" >
                    %for w in widgets:
                        <div class="form-row">
                            <label>
                                ${w[0]}
                            </label>
                            ${w[1].get_html()}
                            %if w[0] == 'Comments':
                                <div class="toolParamHelp" style="clear: both;">
                                    Optional
                                </div>
                            %endif
                        </div>
                    %endfor
                <div class="form-row">
                    <input type="submit" name="add_event_button" value="Save"/>
                </div>
            </form>
        </div>
    </div>
%endif