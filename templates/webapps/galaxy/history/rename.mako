<%inherit file="/base.mako"/>
<%def name="title()">${_('Rename History')}</%def>

<div class="toolForm">
  <div class="toolFormTitle">${_('Rename')}</div>
    <div class="toolFormBody">
        <form action="${h.url_for( controller='history', action='rename' )}" method="post" >
            <div class="form-row">
            <table>
                <thead>
                    <tr>
                        <th>${_('Current Name')}</th>
                        <th>${_('New Name')}</th>
                    </tr>
                </thead>
                <tbody>
                %for history in histories:
                    <tr>
                        <td>
                            <input type="hidden" name="id" value="${trans.security.encode_id( history.id )}">
                            ${history.get_display_name() | h}
                        </td>
                        <td>
                            <input type="text" name="name" value="${history.get_display_name() | h}" size="40">
                        </td>
                    </tr>
                %endfor
                </tbody>
                <tr>
                    <td colspan="2">
                        <input type="submit" name="history_rename_btn" value="${_('Rename Histories')}">
                    </td>
                </tr>
            </table>
            </div>
        </form>
    </div>
</div>
