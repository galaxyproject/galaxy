<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">${_('Rename History')}</%def>

<div class="toolForm">
  <div class="toolFormTitle">${_('Rename History')}</div>
    <div class="toolFormBody">
        <form action="${h.url_for( controller='history', action='rename' )}" method="post" >
            <table class="grid">
                %for history in histories:
                    <tr>
                        <td>
                            <div class="form-row">
                                <input type="hidden" name="id" value="${history.id}">
                                <label>${_('Current Name')}</label>
                                <div style="float: left; width: 250px; margin-right: 10px;">
                                    ${history.name}
                                </div>
                            </div>
                        </td>
                        <td>
                            <div class="form-row">
                                <label>${_('New Name')}</label>
                                <div style="float: left; width: 250px; margin-right: 10px;">
                                    <input type="text" name="name" value="${history.name}" size="40">
                                </div>
                            </div>
                        </td>
                    </tr>
                %endfor
                <tr>
                    <td colspan="2">
                        <div class="form-row">
                            <input type="submit" name="history_rename_btn" value="${_('Rename Histories')}">
                        </div>
                    </td>
                </tr>
            </table>
        </form>
    </div>
</div>
