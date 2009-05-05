<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Browse Libraries</%def>

<h2>
    %if deleted:
        Deleted 
    %endif
    Libraries
</h2>

<ul class="manage-table-actions">
    %if not deleted:
        <li>
            <a class="action-button" href="${h.url_for( controller='admin', action='library', new=True )}"><span>Create a new library</span></a>
        </li>
        <li>
            <a class="action-button" href="${h.url_for( controller='admin', action='deleted_libraries' )}"><span>Manage deleted libraries</span></a>
        </li>
    %endif
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if not libraries:
    %if deleted:
        There are no deleted libraries
    %else:
        There are no libraries.
    %endif
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
                    <td><a href="${h.url_for( controller='admin', action='browse_library', id=library.id, deleted=deleted, show_deleted=show_deleted )}">${library.name}</a></td>
                    <td><i>${library.description}</i></td>
                </tr>             
            %endfor
        </tbody>
    </table>
%endif
