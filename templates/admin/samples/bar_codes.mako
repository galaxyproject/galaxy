<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if message:
    ${render_msg( message, status )}
%endif


<h2>Bar codes for Samples of Request "${request.name}"</h2>
<h3>User: ${user.email}</h3>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='list', operation='show_request', id=trans.security.encode_id(request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>

<div class="toolForm">
    <form name="bar_codes" action="${h.url_for( controller='requests_admin', action='save_bar_codes', request_id=request.id)}" method="post" >
        <table class="grid">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Bar code</th>
                </tr>
            </thead>
            <tbody>
                %for index, sample in enumerate(samples_list):    
                    <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                        <td><b><a>${sample.name}</a></b></td>
                        <td><a>${sample.desc}</a></td>
                        <td>
                            ${widgets[index].get_html()}
                        </td>
                    </tr>             
                %endfor
            </tbody>
        </table>
        <div class="form-row">
            <input type="submit" name="save_bar_codes" value="Save"/>
        </div>
    </form>
</div>