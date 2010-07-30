<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if message:
    ${render_msg( message, status )}
%endif



<h2>Datasets of Sample "${sample.name}"</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', cntrller=cntrller, action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">
        <span>Refresh</span></a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller='library', id=trans.security.encode_id( sample.library.id ) )}">
        <span>${sample.library.name} Data Library</span></a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller=cntrller, action='list', operation='show', id=trans.security.encode_id(sample.request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>


%if len(dataset_files):
    <div class="form-row">
        <table class="grid">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Status</th>
                </tr>
            <thead>
            <tbody>
                %for dataset_index, dataset_file in enumerate(dataset_files):
                    <tr>
                        
                        <td>
                            ${dataset_file.name}
                        </td>
                        <td>
                            ${dataset_file.size}
                        </td>
                        <td>
                            ${dataset_file.status}
                        </td>
                    </tr>
                %endfor
            </tbody>
        </table>
    </div>
%else:
    <div class="form-row">
        There are no dataset files associated with this sample.
    </div>
%endif
