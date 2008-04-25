<%inherit file="/base.mako"/>
<%def name="title()">Rename History</%def>

<div class="toolForm">
  <div class="toolFormTitle">Rename History</div>
  <div class="toolFormBody">
  <form action="${h.url_for( action='history_rename' )}" method="post" >
    <table>
        <tr><th>Current Name</th><th>New Name</th></tr>
        %for history in histories:
        <tr><td>${history.name}<input type="hidden" name="id" value="${history.id}"></td><td><input type="text" name="name" value="${history.name}" size="40"></td></tr>
        %endfor
        <tr><td colspan="2"><input type="submit" name="history_rename_btn" value="Rename Histories"></td></tr>
    </table>
  </form>
  </div>
</div>
</body>
</html>