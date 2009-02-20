<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Browse Libraries</%def>

<h2>Libraries</h2>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if not libraries:
    No libraries contain datasets that you are allowed to access
%else:
    <table class="grid">
        <thead>
            <tr>
                <th>Name</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            %for library in libraries:    
                <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                    <td><a href="${h.url_for( controller='library', action='browse_library', id=library.id )}">${library.name}</a></td>
                    <td><i>${library.description}</i></td>
                </tr>             
            %endfor
        </tbody>
    </table>
%endif
