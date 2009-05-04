<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Share histories</%def>

%if not can_change and not cannot_change:
    <div class="toolForm">
        <div class="toolFormTitle">${_('Share histories')}</div>
        <table>
            <form action="${h.url_for( controller="history", action='share' )}" method="post" >
                <tr><th>${_('History Name:')}</td><th>${_('Number of Datasets:')}</th><th>${_('Share Link')}</th></tr>
                %for history in histories:
                    <tr>
                        <td align="center">${history.name}<input type="hidden" name="id" value="${history.id}"></td>
                        <td align="center">
                            %if len( history.datasets ) < 1:
                                <div class="warningmark">${_('This history contains no data.')}</div>
                            %else:
                                ${len(history.datasets)}
                            %endif
                        </td>
                        <td align="center"><a href="${h.url_for( controller='history', action='imp', id=trans.security.encode_id(history.id) )}">${_('copy link to share')}</a></td>
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
%else:
    <style type="text/css">
        th
        {
            text-align: left;
        }
        td
        {
            vertical-align: top;
        }
    </style>
    <form action="${h.url_for( controller='history', action='share' )}" method="post">
        %for history in histories:
            <input type="hidden" name="id" value="${history.id}">
        %endfor
        <input type="hidden" name="email" value="${email}">
            <div class="warningmessage">
                The history or histories you've chosen to share contain datasets that the user with which you're sharing does not have permission to access.  
                These datasets are shown below.  Datasets that the user has permission to access are not shown.
            </div>
            <p/>
            %if can_change:
                <div class="donemessage">
                    The following datasets can be shared with ${email} by updating their permissions:
                    <p/>
                    <table cellpadding="0" cellspacing="8" border="0">
                        <tr><th>Histories</th><th>Datasets</th></tr>
                        %for history, datasets in can_change.items():
                            <tr>
                                <td>${history.name}</td>
                                <td>
                                    %for dataset in datasets:
                                        ${dataset.name}<br/>
                                    %endfor
                                </td>
                            </tr>
                        %endfor
                    </table>
                </div>
                <p/>
            %endif
            %if cannot_change:
                <div class="errormessage">
                    The following datasets cannot be shared with ${email} because you are not authorized to change the permissions on them.
                    <p/>
                    <table cellpadding="0" cellspacing="8" border="0">
                        <tr><th>Histories</th><th>Datasets</th></tr>
                        %for history, datasets in cannot_change.items():
                            <tr>
                                <td>${history.name}</td>
                                <td>
                                    %for dataset in datasets:
                                        ${dataset.name}<br/>
                                    %endfor
                                </td>
                            </tr>
                        %endfor
                    </table>
                </div>
                <p/>
            %endif
        <div>
            <b>How would you like to proceed?</b>
            <p/>
            %if can_change:
                <input type="radio" name="action" value="public"> Set datasets above to public access
                %if cannot_change:
                    (where possible)
                %endif
                <br/>
                <input type="radio" name="action" value="private"> Set datasets above to private access for me and the user(s) with whom I am sharing
                %if cannot_change:
                    (where possible)
                %endif
                <br/>
            %endif
            <input type="radio" name="action" value="share"> Share anyway
            %if can_change:
                (don't change any permissions)
            %endif
            <br/>
            <input type="radio" name="action" value="no_share"> Don't share<br/>
            <br/>
            <input type="submit" name="submit" value="Ok"><br/>
        </div>
    </form>
%endif
