<%inherit file="/base.mako"/>
<%def name="title()">Copy History Items</%def>

<%def name="javascripts()">

    ${parent.javascripts()}
    ${h.js( "jquery", "galaxy.base" )}
    
    <script type="text/javascript">
        $(function() {
            $("#select-multiple").click(function() {
                $("#single-dest-select").val("");
                $("#single-destination").hide();
                $("#multiple-destination").show();
            });
        });
        %if 'history' in refresh_frames:
            if ( parent.frames && parent.frames.galaxy_history ) {
                parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history')}";
                if ( parent.force_right_panel ) {
                    parent.force_right_panel( 'show' );
                }
            }
        %endif
    </script>
    
</%def>

%if error_msg:
    <p>
        <div class="errormessage">${error_msg}</div>
        <div style="clear: both"></div>
    </p>
%endif
%if done_msg:
    <p>
        <div class="donemessage">${done_msg}</div>
        <div style="clear: both"></div>
    </p>
%endif
<p>
    <div class="infomessage">Copy any number of history items from one history to another.</div>
    <div style="clear: both"></div>
</p>
<p>
    <form method="post">
        <div class="toolForm" style="float: left; width: 45%; padding: 0px;">
            <div class="toolFormTitle">Source History:<br />
                <select id="source_history" name="source_history" refresh_on_change="true" style="font-weight: normal;">
                    %for i, hist in enumerate(target_histories):
                        <%
                            selected = ""
                            current_history_text = ""
                            if hist == source_history:
                                selected = "selected='selected'"
                            if hist == current_history:
                                current_history_text = " (current history)"
                            
                        %>
                        <option value="${trans.security.encode_id(hist.id)}" ${selected}>
                            ${i + 1}: ${h.truncate(hist.name, 30)}${current_history_text}
                        </option>
                    %endfor
                </select>
            </div>
            <div class="toolFormBody">
                %if len(source_datasets) > 0:
                    %for data in source_datasets:
                        <%
                            checked = ""
                            encoded_id = trans.security.encode_id(data.id)
                            if data.id in source_dataset_ids:
                                checked = " checked='checked'"
                        %>
                        <div class="form-row">
                            <input type="checkbox" name="source_dataset_ids" id="dataset_${encoded_id}" value="${encoded_id}"${checked}/>
                            <label for="dataset_${encoded_id}" style="display: inline;font-weight:normal;"> ${data.hid}: ${h.to_unicode(data.name)}</label>
                        </div>
                    %endfor
                %else:
                    <div class="form-row">This history has no datasets.</div>
                %endif
            </div>
        </div>
        <div style="float: left; padding-left: 10px; font-size: 36px;">&rarr;</div>
        <div class="toolForm" style="float: right; width: 45%; padding: 0px;">
            <div class="toolFormTitle">Destination History:</div>
            <div class="toolFormBody">
                <div class="form-row" id="single-destination">
                    <select id="single-dest-select" name="target_history_id">
                        <option value=""></option>
                        %for i, hist in enumerate(target_histories):
                            <%
                                encoded_id = trans.security.encode_id(hist.id)
                                source_history_text = ""
                                selected = ""
                                if hist == source_history:
                                    source_history_text = " (source history)"
                                if encoded_id == target_history_id:
                                    selected = " selected='selected'"
                            %>
                            <option value="${encoded_id}"${selected}>${i + 1}: ${h.truncate(hist.name, 30)}${source_history_text}</option>
                        %endfor
                    </select><br /><br />
                    <a style="margin-left: 10px;" href="javascript:void(0);" id="select-multiple">Choose multiple histories</a>
                </div>
                <div id="multiple-destination" style="display: none;">
                    %for i, hist in enumerate( target_histories ):
                        <%
                            cur_history_text = ""
                            encoded_id = trans.security.encode_id(hist.id)
                            if hist == source_history:
                                cur_history_text = " <strong>(source history)</strong>"
                        %>
                        <div class="form-row">
                            <input type="checkbox" name="target_history_ids" id="hist_${encoded_id}" value="${encoded_id}"/>
                            <label for="hist_${encoded_id}" style="display: inline; font-weight:normal;">${i + 1}: ${hist.name}${cur_history_text}</label>
                        </div>
                    %endfor
                </div>
                %if trans.get_user():
                    <%
                        checked = ""
                        if "create_new_history" in target_history_ids:
                            checked = " checked='checked'"
                    %>
                    <hr />
                    <div style="text-align: center; color: #888;">&mdash; OR &mdash;</div>
                    <div class="form-row">
                        <label for="new_history_name" style="display: inline; font-weight:normal;">New history named:</label>
                        <input type="textbox" name="new_history_name" />
                    </div>
                %endif
            </div>
        </div>
            <div style="clear: both"></div>
            <div class="form-row" align="center">
                <input type="submit" class="primary-button" name="do_copy" value="Copy History Items"/>
            </div>
        </form>
    </div>
</p>
