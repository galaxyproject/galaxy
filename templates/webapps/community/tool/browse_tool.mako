<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="title()">Browse Tool</%def>

<h2>Galaxy Tool</h2>

%if message:
    ${render_msg( message, status )}
%endif

%if not tools:
    There are no tools
%else:
    <table class="grid">
        <thead>
            <tr>
                <th>Name</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>   
            <tr class="formRow id="toolRow">
                <td><a href="${h.url_for( controller='tool_browser', action='browse', id=trans.security.encode_id( tool.id ) )}">${tool.name}</a></td>
                <td>${tool.description}</td>
            </tr>             
        </tbody>
    </table>
%endif
