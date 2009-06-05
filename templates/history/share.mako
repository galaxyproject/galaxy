<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Share histories</%def>

<div class="toolForm">
    <div class="toolFormTitle">Share ${len( histories)} histories</div>
    <div class="toolFormBody">
        %if not can_change and not cannot_change:
            <form action="${h.url_for( controller="history", action='share' )}" method="post" >
                %for history in histories:
                    <div class="toolForm">
                        <div class="form-row">
                            <label>${_('History Name:')}</label>
                            <div style="float: left; width: 250px; margin-right: 10px;">
                                ${history.name}<input type="hidden" name="id" value="${history.id}">
                            </div>
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <label>${_('Number of Datasets:')}</label>
                            <div style="float: left; width: 250px; margin-right: 10px;">
                                %if len( history.datasets ) < 1:
                                    <div class="warningmark">${_('This history contains no data.')}</div>
                                %else:
                                    ${len(history.datasets)}
                                %endif
                                </td>
                            </div>
                        </div>
                        ## TODO: this feature is not currently working
                        ##<div style="clear: both"></div>
                        ##<div class="form-row">
                        ##    <label>${_('Share Link')}</label>
                        ##    <div style="float: left; width: 250px; margin-right: 10px;">
                        ##        <a href="${h.url_for( controller='history', action='imp', id=trans.security.encode_id(history.id) )}">${_('copy link to share')}</a>
                        ##    </div>
                        ##</div>
                        ##<div style="clear: both"></div>
                        <p/>
                    </div>
                %endfor
                <p/>
                <div style="clear: both"></div>
                <div class="form-row">
                    <label>Galaxy user emails with which to share histories</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="email" value="${email}" size="40">
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Enter a Galaxy user email address or a comma-separated list of addresses if sharing with multiple users
                    </div>
                </div>
                %if send_to_err:
                    <div style="clear: both"></div>
                    <div class="form-row">
                        <div class="errormessage">${send_to_err}</div>
                    </div>
                %endif
                <div style="clear: both"></div>
                <div class="form-row">
                    <input type="submit" name="history_share_btn" value="Submit">
                </div>
            </form>
        %else:
            <form action="${h.url_for( controller='history', action='share' )}" method="post">
                %for history in histories:
                    <input type="hidden" name="id" value="${history.id}">
                %endfor
                <input type="hidden" name="email" value="${email}">
                %if no_change_needed:
                    <div style="clear: both"></div>
                    <div class="form-row">
                        <div class="donemessage">
                            The following datasets can be shared with ${email} with no changes
                        </div>
                    </div>
                    %for history, hdas in no_change_needed.items():
                        <div class="form-row">
                            <label>History</label>
                            ${history.name}
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <label>Datasets</label>
                        </div>
                        %for hda in hdas:
                            <div class="form-row">
                                ${hda.name}
                            </div>
                        %endfor
                    %endfor
                %endif
                %if can_change:
                    <div style="clear: both"></div>
                    <div class="form-row">
                        <div class="warningmessage">
                            The following datasets can be shared with ${email} by updating their permissions
                        </div>
                    </div>
                    %for history, hdas in can_change.items():
                        <div class="form-row">
                            <label>History</label>
                            ${history.name}
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <label>Datasets</label>
                        </div>
                        %for hda in hdas:
                            <div class="form-row">
                                ${hda.name}
                            </div>
                        %endfor
                    %endfor
                %endif
                %if cannot_change:
                    <div style="clear: both"></div>
                    <div class="form-row">
                        <div class="errormessage">
                            The following datasets cannot be shared with ${email} because you are not authorized to 
                            change the permissions on them
                        </div>
                    </div>
                    %for history, hdas in cannot_change.items():
                        <div class="form-row">
                            <label>History</label>
                            ${history.name}
                        </div>
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <label>Datasets</label>
                        </div>
                        %for hda in hdas:
                            <div class="form-row">
                                ${hda.name}
                            </div>
                        %endfor
                    %endfor
                %endif
                <div class="form-row">
                    <label>How would you like to proceed?</label>
                </div>
                %if can_change:
                    <div class="form-row">
                        <input type="radio" name="action" value="public"> Make datasets public so anyone can access them 
                        %if cannot_change:
                            (where possible)
                        %endif
                    </div>
                    <div class="form-row">
                        <input type="radio" name="action" value="private"> Make datasets private to me and the user(s) with whom I am sharing
                        %if cannot_change:
                            (where possible)
                        %endif
                    </div>
                %endif
                %if no_change_needed:
                    <div class="form-row">
                        <input type="radio" name="action" value="share"> Share anyway
                        %if can_change:
                            (don't change any permissions)
                        %endif
                    </div>
                %endif
                <div class="form-row">
                    <input type="radio" name="action" value="no_share"> Don't share
                </div>
                <div class="form-row">
                    <input type="submit" name="share_proceed_button" value="Go"><br/>
                </div>
            </form>
        %endif
    </div>
</div>
