<% _=n_ %>
<%inherit file="/base.mako"/>
<%def name="title()">Share histories</%def>

<div class="toolForm">
    <div class="toolFormTitle">Share ${len( histories)} histories</div>
    <div class="toolFormBody">
        %if not can_change and not cannot_change and not no_change_needed:
            ## We are sharing histories that contain only public datasets
            <form name='share' id='share' action="${h.url_for( controller='history', action='share' )}" method="post" >
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
                                        ${ util.unicodify( history.name ) | h }
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
                    <% existing_emails = ','.join([ d.user.email for d in history.users_shared_with ]) %>
                    <label>Galaxy user emails with which to share histories</label>
                    %if trans.app.config.expose_user_email or trans.app.config.expose_user_name or trans.user_is_admin:
                    <input type="hidden" id="email_select" name="email" value="${ existing_emails }" style="float: left; width: 250px; margin-right: 10px;">
                    </input>
                    %else:
                    <input type="text" name="email" value="${ existing_emails }" size="40">
                    </input>
                    %endif
                    <div class="toolParamHelp" style="clear: both;">
                        Enter a Galaxy user email address or a comma-separated list of addresses if sharing with multiple users
                    </div>
                </div>
                %if send_to_err:
                    <div style="clear: both"></div>
                    <div class="form-row">
                        <div class="alert alert-danger">${send_to_err}</div>
                    </div>
                %endif
                <div style="clear: both"></div>
                <div class="form-row">
                    <input type="submit" name="share_button" value="Submit">
                </div>
            </form>
            <script type="text/javascript">
            // stolen from templates/admin/impersonate.mako
            /*  This should be ripped out and made generic at some point for the
             *  various API bindings available, and once the API can filter list
             *  queries (term, below) */

            var user_id = "${trans.security.encode_id(trans.user.id)}";
            var history_id = "${trans.security.encode_id( history.id )}";

            function item_to_label(item){
                var text = "";
                if(typeof(item.username) === "string" && typeof(item.email) === "string"){
                    text = item.username + " <" + item.email + ">";
                }else if(typeof(item.username) === "string"){
                    text = item.username;
                }else{
                    text = item.email;
                }
                return text;
                //return "id:" + item.id + "|e:" + item.email + "|u:" + item.username;
            }

            $("#email_select").select2({
                placeholder: "Select a user",
                multiple: true,
                initSelection: function(element, callback) {
                    var data = [
                    // Must be here to loop across the users that this has been shared with.
                    %for i, association in enumerate( history.users_shared_with ):
                        <% shared_with = association.user %>
                        {
                            email: "${ shared_with.email }",
                            id: "${trans.security.encode_id(shared_with.id)}",
                            text: item_to_label({"email": "${ shared_with.email }", "username": "${ shared_with.username }" })
                        }, 
                    %endfor
                    ];
                    callback(data);
                },
                tokenSeparators: [',', ' '],
                // Required for initSelection
                id: function(object) {
                    return object.id;
                },
                ajax: {
                    url: "${h.url_for(controller="/api/users", action="index")}",
                    data: function (term) {
                        return {
                            f_any: term,
                        };
                    },
                    dataType: 'json',
                    quietMillis: 250,
                    results: function (data) {
                        var results = [];
                        // For every user returned by the API call,
                        $.each(data, function(index, item){
                            // If they aren't the requesting user, add to the
                            // list that will populate the select
                            if(item.id != "${trans.security.encode_id(trans.user.id)}"){
                                if(item.email !== undefined){
                                    results.push({
                                      id: item.id,
                                      name: item.username,
                                      text: item_to_label(item),
                                    });
                                }
                            }
                        });
                        return {
                            results: results
                        };
                    }
                },
                createSearchChoice: function(term, data) {
                    // Check for a user with a matching email.
                    var matches = _.filter(data, function(user){
                        return user.text.indexOf(term) > -1;
                    });
                    // If there aren't any users with matching object labels, then 
                    // display a "default" entry with whatever text they're entering.
                    // id is set to term as that will be used in 
                    if(matches.length == 0){
                        return {id: term, text:term};
                    }else{
                        // No extra needed
                    }
                }
            });
            </script>
        %else:
            ## We are sharing restricted histories
            %if no_change_needed or can_change:
                <form name='share_restricted' id=share_restricted' action="${h.url_for( controller='history', action='share_restricted' )}" method="post">
                    %if send_to_err:
                        <div style="clear: both"></div>
                        <div class="form-row">
                            <div class="alert alert-danger">${send_to_err}</div>
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
                                ${util.unicodify( history.name )}
                            </div>
                            <div style="clear: both"></div>
                            <div class="form-row">
                                <label>Datasets</label>
                            </div>
                            %for hda in hdas:
                                <div class="form-row">
                                    ${util.unicodify( hda.name )}
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
                                ${util.unicodify( history.name )}
                            </div>
                            <div style="clear: both"></div>
                            <div class="form-row">
                                <label>Datasets</label>
                            </div>
                            %for hda in hdas:
                                <div class="form-row">
                                    ${util.unicodify( hda.name )}
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
                            <div class="alert alert-danger">
                                The following datasets cannot be shared with ${email} because you are not authorized to 
                                change the permissions on them
                            </div>
                        </div>
                        %for history, hdas in cannot_change.items():
                            <div class="form-row">
                                <label>History</label>
                                ${util.unicodify( history.name )}
                            </div>
                            <div style="clear: both"></div>
                            <div class="form-row">
                                <label>Datasets</label>
                            </div>
                            %for hda in hdas:
                                <div class="form-row">
                                    ${util.unicodify( hda.name )}
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
