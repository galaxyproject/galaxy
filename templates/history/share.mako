<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Share histories</%def>

<div class="toolForm">
    <div class="toolFormTitle">Share ${len( histories)} histories</div>
    <div class="toolFormBody">
        %if not can_change and not cannot_change and not no_change_needed:
            ## We are sharing histories that contain only public datasets
            <form name='share' id='share' action="${h.url_for( action='share' )}" method="post" >
                <div class="form-title-row"><b>Histories to be shared:</b></div>
                <div class="form-row" style="padding-left: 2em;">
                    <table width="100%">
                        <thead>
                            <th>${_('History Name')}</th>
                            <th>${_('Number of Datasets')}</th>
                        </thead>
                        <tbody>
                            %for history in histories:
                                <tr>
                                    <td>
                                        <input type="hidden" name="id" value="${trans.security.encode_id( history.id )}">
                                        ${history.name}
                                    </td>
                                    <td>
                                        %if len( history.datasets ) < 1:
                                            <div class="warningmark">${_('This history contains no data.')}</div>
                                        %else:
                                            ${len(history.datasets)}
                                        %endif
                                    </td>
                                </tr>
                            %endfor
                        </tbody>
                    </table>
                </div>
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
                    <input type="submit" name="share_button" value="Submit">
                </div>
            </form>
        %else:
            ## We are sharing restricted histories
            %if no_change_needed or can_change:
                <form name='share_restricted' id=share_restricted' action="${h.url_for( controller='history', action='share_restricted' )}" method="post">
                    %if send_to_err:
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <div class="errormessage">${send_to_err}</div>
                        </div>
                    %endif
                    ## Needed for rebuilding dicts
                    <input type="hidden" name="email" value="${email}" size="40">
                    %for history in histories:
                        <input type="hidden" name="id" value="${trans.security.encode_id( history.id )}">
                    %endfor
                    %if no_change_needed:
                        ## no_change_needed looks like: {historyX : [hda, hda], historyY : [hda] }
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
                                    %if hda.deleted:
                                        (deleted)
                                    %endif
                                </div>
                            %endfor
                        %endfor
                    %endif
                    %if can_change:
                        ## can_change looks like: {historyX : [hda, hda], historyY : [hda] }
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
                                    %if hda.deleted:
                                        (deleted)
                                    %endif
                                </div>
                            %endfor
                        %endfor
                    %endif
                    %if cannot_change:
                        ## cannot_change looks like: {historyX : [hda, hda], historyY : [hda] }
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
                                    %if hda.deleted:
                                        (deleted)
                                    %endif
                                </div>
                            %endfor
                        %endfor
                    %endif
                    <div class="toolFormTitle"></div>
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
                            %if no_change_needed:
                                <input type="radio" name="action" value="private"> Make datasets private to me and the user(s) with whom I am sharing
                            %else:
                                <input type="radio" name="action" value="private" checked> Make datasets private to me and the user(s) with whom I am sharing
                            %endif
                            %if cannot_change:
                                (where possible)
                            %endif
                        </div>
                    %endif
                    %if no_change_needed:
                        <div class="form-row">
                            <input type="radio" name="action" value="share_anyway" checked> Share anyway
                            %if can_change:
                                (don't change any permissions)
                            %endif
                        </div>
                    %endif
                    <div class="form-row">
                        <input type="submit" name="share_restricted_button" value="Go"><br/>
                    </div>
                </form>
            %endif
        %endif
    </div>
</div>
