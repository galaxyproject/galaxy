<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">${_('Rename History')}</%def>

<div class="toolForm">
  <div class="toolFormTitle">${_('Rename History')}</div>
  <div class="toolFormBody">
  <form action="${h.url_for( controller='history', action='rename' )}" method="post" >
    <table>
        <tr><th>${_('Current Name')}</th><th>${_('New Name')}</th></tr>
        %for history in histories:
        <tr><td>${history.name}<input type="hidden" name="id" value="${history.id}"></td><td><input type="text" name="name" value="${history.name}" size="40"></td></tr>
        %endfor
        <tr><td colspan="2"><input type="submit" name="history_rename_btn" value="${_('Rename Histories')}"></td></tr>
    </table>
  </form>
  </div>
</div>
</body>
</html>