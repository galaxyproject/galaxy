<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Browse Samples</%def>

<h2>Samples</h2>

<ul class="manage-table-actions">
    %if not deleted:
        <li>
            <a class="action-button" href="${h.url_for( controller='sample', action='do', new=True )}"><span>Add Sample</span></a>
        </li>
    %endif
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if not samples_list:
    You have no samples.
%else:
    <table class="grid">
        <thead>
            <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Type</th>
                <th>State</th>
            </tr>
        </thead>
        <tbody>
            %for id, name, desc, st, state in samples_list:    
                <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                    <td><b><a href="${h.url_for( controller='sample', action='do', sample_id=id, edit=True)}">${name}</a></b></td>
                    <td><a>${desc}</a></td>
                    <td><a>${st}</a></td>
                    <td><a href="${h.url_for( controller='sample', action='events', sample_id=id)}">${state}</a></td>
                </tr>             
            %endfor
        </tbody>
    </table>
%endif