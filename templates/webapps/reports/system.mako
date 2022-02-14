<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.web.framework.helpers import time_ago
%>

%if message:
    ${render_msg( message, 'done' )}
%endif

<div class="report">
    <h3 align="center">Old Histories and Datasets</h3>
    <table id="systemForm" class="border">
        <tr>
            <td>
                <form method="post" action="system">
                    <p>
                        <button name="action" value="userless_histories">
                            Number of Histories
                        </button>
                        that are not associate with a user and were last
                        updated more than
                        <input type="textfield"
                               value="${userless_histories_days}"
                               size="3"
                               name="userless_histories_days">
                        days ago.
                    </p>
                    <p>
                        <button name="action" value="deleted_histories">
                            Number of Histories
                        </button>
                        that were deleted more than 
                        <input type="textfield" 
                               value="${deleted_histories_days}"
                               size="3"
                               name="deleted_histories_days"> 
                        days ago but have not yet been purged.
                    </p>
                    <p>
                        <button name="action" value="deleted_datasets">
                            Number of Datasets
                        </button> 
                        that were deleted more than 
                        <input type="textfield" 
                               value="${deleted_datasets_days}"
                               size="3"
                               name="deleted_datasets_days"> 
                        days ago but have not yet been purged.
                    </p>
                </form>
            </td>
        </tr>
    </table>
    <br clear="left" />
    <h3 align="center">Current Disk Space Where Datasets are Stored</h3>
    <table align="center" width="90%" class="colored">
        <tr>
            <td colspan="5">
                <b>Disk Usage for ${file_path}</b>
            </td>
        </tr>
        <tr class="header">
            <td>Disk Size</td>
            <td>Used</td>
            <td>Available</td>
            <td>Percent Used</td>
        </tr>
        <tr class="tr">
            <td>${disk_usage[0]}</td>
            <td>${disk_usage[1]}</td>
            <td>${disk_usage[2]}</td>
            <td>${disk_usage[3]}</td>
        </tr>
    </table>
    <br clear="left" />
    %if datasets.count() > 0:
        <h3 align="center">
            ${datasets.count()} largest unpurged data files over
            ${file_size_str}
        </h3>
        <table align="center" width="90%" class="colored">
            <tr class="header">
                <td>File</td>
                <td>Last Updated</td>
                <td>Deleted</td>
                <td>File Size</td>
            </tr>
            <% ctr = 0 %>
            %for dataset in datasets:
                %if ctr % 2 == 1:
                    <tr class="odd_row">
                %else:
                    <tr class="tr">
                %endif
                    <td>
                        <% dataset_label = 'dataset_%d.dat' % dataset.id %>
                        <a href="${h.url_for( controller='system', action='dataset_info', id=trans.security.encode_id( dataset.id ) )}">
                            ${dataset_label}
                        </a>
                    </td>
                    <td>${time_ago( dataset.update_time )}</td>
                    <td>${dataset.deleted}</td>
                    <td>${nice_size( dataset.file_size, True )}</td>
                </tr>
                <% ctr += 1 %>
            %endfor
        </table>
        <br clear="left" />
    %else:
        <h3 align="center">
            There are no unpurged data files larger than ${file_size_str}
        </h3>
    %endif
</div>
