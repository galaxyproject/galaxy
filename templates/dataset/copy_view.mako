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
    <div class="toolForm">
        <form>
            <div style="float: left; width: 50%; padding: 0px;">
                <div class="toolFormTitle">Source History Items</div>
                <div class="toolFormBody">
                    %for data in source_datasets:
                        <%
                            checked = ""
                            if data.id in source_dataset_ids:
                                checked = " checked='checked'"
                        %>
                        <div class="form-row">
                            <input type="checkbox" name="source_dataset_ids" id="dataset_${data.id}" value="${data.id}"${checked}/>
                            <label for="dataset_${data.id}" style="display: inline;font-weight:normal;"> ${data.hid}: ${data.name}</label>
                        </div>
                    %endfor 
                </div>
            </div>
            <div style="float: right; width: 50%; padding: 0px;">
                <div class="toolFormTitle">Target Histories</div>
                <div class="toolFormBody">
                    %for i, hist in enumerate( target_histories ):
                        <%
                            checked = ""
                            if hist.id in target_history_ids:
                                checked = " checked"
                            cur_history_text = ""
                            if hist == trans.get_history():
                                cur_history_text = " <strong>(current history)</strong>"
                        %>
                        <div class="form-row">
                            <input type="checkbox" name="target_history_ids" id="hist_${hist.id}" value="${hist.id}"${checked}/>
                            <label for="hist_${hist.id}" style="display: inline;font-weight:normal;">${i + 1}: ${hist.name}${cur_history_text}</label>
                        </div>
                    %endfor
                    %if trans.get_user():
                        <%
                            checked = ""
                            if "create_new_history" in target_history_ids:
                                checked = " checked='checked'"
                        %>
                        <br/>
                        <div class="form-row"><input type="checkbox" name="target_history_ids" value="create_new_history"${checked}/>New history named: <input type="textbox" name="new_history_name" value="${new_history_name}"/></div>
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
