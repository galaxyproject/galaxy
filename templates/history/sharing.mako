<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/display_base.mako" import="get_history_link" />

##<h2>Import via link</h2>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<h2>Histories that you've shared with others or enabled to be imported</h2>

%if not histories:
    You have no histories that you've shared with others or enabled to be imported
%else:
    %for history in histories:
        <div class="toolForm">
            <div class="toolFormTitle">History '${history.get_display_name()}' shared with</div>
            <div class="toolFormBody">
                <div class="form-row">
                    <div style="float: right;">
                        <a class="action-button" href="${h.url_for( controller='history', action='share', id=trans.security.encode_id( history.id ) )}">
                            <span>Share with another user</span>
                        </a>
                    </div>
                </div>
                %if history.users_shared_with:
                    %for i, association in enumerate( history.users_shared_with ):
                        <% user = association.user %>
                        <div class="form-row">
                            <a class="action-button" href="${h.url_for( controller='history', action='sharing', id=trans.security.encode_id( history.id ), unshare_user=trans.security.encode_id( user.id ) )}">Unshare</a>
                            ${user.email}
                        </div>
                    %endfor
                %endif
                %if history.importable:
                    <div class="form-row">
                        <% url = get_history_link( history, True )%>
                        <a href="${url}" target="_blank">${url}</a>
                        <div class="toolParamHelp" style="clear: both;">
                            Send the above link to users as an easy way for them to view the history.
                        </div>
                    </div>
                    <div class="form-row">
                        <% url = h.url_for( controller='history', action='imp', id=trans.security.encode_id(history.id), qualified=True ) %>
                        <a href="${url}">${url}</a>
                        <div class="toolParamHelp" style="clear: both;">
                            Send the above link to users as an easy way for them to import the history, making a copy of their own.
                        </div>
                    </div>
                    <div class="form-row">
                        <form action="${h.url_for( controller='history', action='sharing', id=trans.security.encode_id( history.id ) )}" method="POST">
                            <div class="form-row">
                                <input class="action-button" type="submit" name="disable_import_via_link" value="Disable import via link">
                            </div>
                        </form>
                    </div>
                %else:
                    <form action="${h.url_for( action='sharing', id=trans.security.encode_id(history.id) )}" method="POST">
                        <div class="form-row">
                            <input class="action-button" type="submit" name="enable_import_via_link" value="Enable import via link">
                            <div class="toolParamHelp" style="clear: both;">
                                Click to generate a URL that you can give to a user to allow them to import this history, making a copy of their own
                            </div>
                        </div>
                    </form>
                %endif
            </div>
        </div>
    %endfor
%endif
