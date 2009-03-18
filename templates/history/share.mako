<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">${_('Share histories')}</%def>

<div class="toolForm">
<div class="toolFormTitle">${_('Share Histories')}</div>
<table>
<form action="${h.url_for( action='history_share' )}" method="post" >
    <tr><th>${_('History Name:')}</td><th>${_('Number of Datasets:')}</th><th>${_('Share Link')}</th></tr>
    %for history in histories:
    <tr><td align="center">${history.name}<input type="hidden" name="id" value="${history.id}"></td><td align="center">
    
    %if len(history.datasets) < 1:
    <div class="warningmark">
    ${_('This history contains no data.')}
    </div>
    %else:
    ${len(history.datasets)}
    %endif
    </td>
    <td align="center"><a href="${h.url_for( action='history_import', id=history.id )}">${_('copy link to share')}</a></td>
    </tr>
    %endfor
    <tr><td>${_('Email of User to share with:')}</td><td><input type="text" name="email" value="${email}" size="40"></td></tr>
    %if send_to_err:
    <tr><td colspan="100%"><div class="errormessage">${send_to_err}</div></td></tr>
    %endif
    <tr><td colspan="2" align="right"><input type="submit" name="history_share_btn" value="Submit"></td></tr>
</form>
</table>
</div>