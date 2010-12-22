<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="javascripts" />
<%def name="title()">Copy History Items</%def>

${javascripts()}

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
    <div class="infomessage">Select any number of source history items and any number of target histories and click "Copy History Items" to add a copy of each selected history item to each selected target history.</div>
    <div style="clear: both"></div>
</p>
<p>
    <form method="post">
        <div class="toolForm" style="float: left; width: 45%; padding: 0px;">
            <div class="toolFormTitle" style="height: 20px;">Source History:
                <select id="source_history" name="source_history" refresh_on_change="true">
                    %for hist in target_histories:
                        <%
                            selected = ""
                            if hist == source_history:
                                selected = "selected='selected'"
                        %>
                        <option value="${trans.security.encode_id(hist.id)}" ${selected}>${hist.name}</option>
                    %endfor
                </select>
            </div>
            <div class="toolFormBody">
                %for data in source_datasets:
                    <%
                        checked = ""
                        encoded_id = trans.security.encode_id(data.id)
                        if data.id in source_dataset_ids:
                            checked = " checked='checked'"
                    %>
                    <div class="form-row">
                        <input type="checkbox" name="source_dataset_ids" id="dataset_${encoded_id}" value="${encoded_id}"${checked}/>
                        <label for="dataset_${encoded_id}" style="display: inline;font-weight:normal;"> ${data.hid}: ${data.name}</label>
                    </div>
                %endfor 
            </div>
        </div>
        <div class="toolForm" style="float: right; width: 45%; padding: 0px;">
            <div class="toolFormTitle">Target Histories</div>
            <div class="toolFormBody">
                %for i, hist in enumerate( target_histories ):
                    <%
                        checked = ""
                        encoded_id = trans.security.encode_id(hist.id)
                        if hist.id in target_history_ids:
                            checked = " checked='checked'"
                        cur_history_text = ""
                        if hist == source_history:
                            cur_history_text = " <strong>(source history)</strong>"
                    %>
                    <div class="form-row">
                        <input type="checkbox" name="target_history_ids" id="hist_${encoded_id}" value="${encoded_id}"${checked}/>
                        <label for="hist_${encoded_id}" style="display: inline; font-weight:normal;">${i + 1}: ${hist.name}${cur_history_text}</label>
                    </div>
                %endfor
                %if trans.get_user():
                    <%
                        checked = ""
                        if "create_new_history" in target_history_ids:
                            checked = " checked='checked'"
                    %>
                    <br/>
                    <div class="form-row"><input type="checkbox" name="target_history_ids" id="create_new_history" value="create_new_history"${checked}/>
                        <label for="create_new_history" style="display: inline; font-weight:normal;"> New history named:</label> <input type="textbox" name="new_history_name" value="${new_history_name}"/>
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
