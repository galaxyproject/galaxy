<%inherit file="/base.mako"/>
<html>
  <head>
    <title>Galaxy System Management</title>
    <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
  </head>
  <body>
    <h3 align="center">Old Histories and Datasets</h3>
    %if msg:
      <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
        <tr><td class="ok_bgr">${msg}</td></tr>
      </table>
    %endif
    <table align="center" width="70%" class="border" cellpadding="5" cellspacing="5">
      <tr>
        <td>
          <form method="post" action="system">
            <p>
              <button name="action" value="userless_histories">Number of Histories</button>
              that are not associate with a user and were last updated more than 
              <input type="textfield" value="${userless_histories_days}" size="3" name="userless_histories_days"> 
              days ago.
            </p>
            <p>
              <button name="action" value="deleted_histories">Number of Histories</button>
              that were deleted more than 
              <input type="textfield" value="${deleted_histories_days}" size="3" name="deleted_histories_days"> 
              days ago but have not yet been purged.
            </p>
            <p>
              <button name="action" value="deleted_datasets">Number of Datasets</button> 
              that were deleted more than 
              <input type="textfield" value="${deleted_datasets_days}" size="3" name="deleted_datasets_days"> 
              days ago but have not yet been purged.
            </p>
          </form>
        </td>
      </tr>
    </table>
    <br clear="left" /><br />
    <h3 align="center">Current Disk Space Where Datasets are Stored</h3>
    <table align="center" width="60%" class="colored">
      <tr><td colspan="5"><div class="reportTitle">Disk Usage for ${file_path}</div></td></tr>
      <tr class="header">
        <td>File System</td>
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
        <td>${disk_usage[4]}</td>
      </tr>
      %if len( datasets ) == 0:
        <tr class="header"><td colspan="5">There are no datasets larger than ${file_size_str}</td></tr>
      %else:
        <tr><td colspan="5"><div class="reportTitle">${len( datasets )} largest datasets over ${file_size_str}</div></td></tr>
        <tr class="header">
          <td>File</td>
          <td>Last Updated</td>
          <td>History ID</td>
          <td>Deleted</td>
          <td>Size on Disk</td>
        </tr>
        <%
          ctr = 0
        %>
        %for dataset in datasets:
          %if len( datasets ) > 2 and ctr % 2 == 1:
            <tr class="odd_row">
          %else:
            <tr class="tr">
          %endif
            <td>dataset_${dataset[0]}.dat</td>
            <td>${dataset[1]}</td>
            <td>${dataset[2]}</td>
            <td>${dataset[3]}</td>
            <td>${dataset[4]}</td>
          </tr>
          <%
            ctr += 1
          %>
        %endfor
      %endif
    </table>
  </body>
</html>
