<%inherit file="/base.mako"/>
<%namespace file="/refresh_frames.mako" import="handle_refresh_frames" />

<%def name="title()">Copy History Items</%def>

<%def name="javascripts()">

    ${parent.javascripts()}

    ${handle_refresh_frames()}
    
    <script type="text/javascript">
        $(function() {
            $("#select-multiple").click(function() {
                $("#single-dest-select").val("");
                $("#single-destination").hide();
                $("#multiple-destination").show();
            });
        });
        $(function() {
            $("#source-content-all").click(function() {
                $("input[name='source_content_ids']").each(function() {
                    this.checked = true;
                });
            });
        });
        $(function() {
            $("#source-content-none").click(function() {
                $("input[name='source_content_ids']").each(function() {
                    this.checked = false;
                });
            });
        });
    </script>
    
</%def>

%if error_msg:
    <div>
        <div class="errormessage">${error_msg}</div>
        <div style="clear: both"></div>
    </div>
%endif
%if done_msg:
    <div>
        <div class="donemessage">${done_msg}</div>
        <div style="clear: both"></div>
    </div>
%endif
<div>
    <div class="infomessage">Copy any number of history items from one history to another.</div>
    <div style="clear: both"></div>
</div>
<div>
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
                            ${i + 1}: ${h.truncate(util.unicodify( hist.name ), 30) | h}${current_history_text}
                        </option>
                    %endfor
                </select>
            </div>
            <div class="toolFormBody">
                <% has_source_contents = False %>
                %for data in source_contents:
                    %if not has_source_contents:
                        <div class="form-row">
                            <div class="btn-group">
                                <span class="select-all btn btn-default" name="source-content-all" id="source-content-all">All</span>
                                <span class="deselect-all btn btn-default" name="source-content-none" id="source-content-none">None</span>
                            </div>
                        </div>
                    %endif
                    <%
                        has_source_contents = True
                        checked = ""
                        encoded_id = trans.security.encode_id(data.id)
                        input_id = "%s|%s" % ( data.history_content_type, encoded_id )
                        if input_id in source_content_ids:
                            checked = " checked='checked'"
                    %>
                    <div class="form-row">
                        <input type="checkbox" name="source_content_ids" id="${input_id}" value="${input_id}"${checked}/>
                        <label for="${input_id}" style="display: inline;font-weight:normal;"> ${data.hid}: ${h.to_unicode(data.name) | h}</label>
                    </div>
                %endfor
                %if not has_source_contents:
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
                            <option value="${encoded_id}"${selected}>${i + 1}: ${h.truncate( util.unicodify( hist.name ), 30) | h}${source_history_text}</option>
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
                            <label for="hist_${encoded_id}" style="display: inline; font-weight:normal;">${i + 1}: ${ util.unicodify( hist.name ) | h }${cur_history_text}</label>
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
                        <input id="new_history_name" type="text" name="new_history_name" />
                    </div>
                %endif
            </div>
        </div>
        <div style="clear: both"></div>
        <div class="form-row" style="text-align: center;">
            <input type="submit" class="primary-button" name="do_copy" value="Copy History Items"/>
        </div>
    </form>
</div>
