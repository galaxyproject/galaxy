<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<script type="text/javascript">
$(document).ready(function(){
    //hide the all of the element with class msg_body
    $(".msg_body").hide();
    //toggle the componenet with class msg_body
    $(".msg_head").click(function(){
        $(this).next(".msg_body").slideToggle(450);
    });
});
</script>
<style type="text/css">
.msg_head {
    padding: 0px 0px;
    cursor: pointer;
}

}
</style>


<h2>Data transfer from Sequencer</h2>
<h3>Sample "${sample.name}" of Request "${sample.request.name}"</h3>

<ul class="manage-table-actions">
    %if sample.request.submitted() and sample.inprogress_dataset_files():
    <li>
        <a class="action-button" href="${h.url_for( controller='requests', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">
        <span>Refresh this page</span></a>
    </li>
    %endif
    %if sample.library:
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller='library', id=trans.security.encode_id( sample.library.id ) )}">
        <span>${sample.library.name} Data Library</span></a>
    </li>
    %endif
    <li>
        <a class="action-button" href="${h.url_for( controller='requests', action='list', operation='show_request', id=trans.security.encode_id(sample.request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>

<div class="toolForm">
    <form name="get_data" action="${h.url_for( controller='requests_admin', action='get_data', sample_id=sample.id)}" method="post" >
        <div class="form-row">
            %if len(dataset_files):
                <table class="grid">
                    <thead>
                        <tr>
                            <th>Dataset File</th>
                            <th>Transfer Status</th>
                        </tr>
                    <thead>
                    <tbody>
                        %for dataset_index, dataset_file in enumerate(dataset_files):
                            ${sample_dataset_files( dataset_index, dataset_file[0], dataset_file[1] )}
                        %endfor
                    </tbody>
                </table>
            %else:
                There are no dataset files.
            %endif
        </div>
    </form>
</div>

<%def name="sample_dataset_files( dataset_index, dataset_file, status )">
    <tr>
        <td>${dataset_file.split('/')[-1]}</td>
        <td>
            %if status == sample.transfer_status.IN_PROGRESS: 
                <i>${status}</i>
            %else:
                ${status}
            %endif
        </td>
    </tr>
</%def>