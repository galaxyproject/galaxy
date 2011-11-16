<%namespace file="/message.mako" import="render_msg" />
<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="javascripts" />
<%def name="title()">Import library datasets to histories</%def>

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
    </script>    
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<b>Import library datasets into histories</b>
<br/><br/>
<form action="${h.url_for( controller='library_common', action='import_datasets_to_histories', cntrller=cntrller, use_panels=use_panels, show_deleted=show_deleted )}" method="post">
    <div class="toolForm" style="float: left; width: 45%; padding: 0px;">
        <div class="toolFormBody">
            %if source_lddas:
                %for source_ldda in source_lddas:
                    <%
                        checked = ""
                        encoded_id = trans.security.encode_id( source_ldda.id )
                        if source_ldda.id in ldda_ids:
                            checked = " checked='checked'"
                    %>
                    <div class="form-row">
                        <input type="checkbox" name="ldda_ids" id="dataset_${encoded_id}" value="${encoded_id}" ${checked}/>
                        <label for="dataset_${encoded_id}" style="display: inline;font-weight:normal;">${source_ldda.name}</label>
                    </div>
                %endfor
            %else:
                <div class="form-row">This folder has no accessible library datasets.</div>
            %endif
        </div>
    </div>
    <div style="float: left; padding-left: 10px; font-size: 36px;">&rarr;</div>
    <div class="toolForm" style="float: right; width: 45%; padding: 0px;">
        <div class="toolFormTitle">Destination Histories:</div>
        <div class="toolFormBody">
            <div class="form-row" id="single-destination">
                <select id="single-dest-select" name="target_history_id">
                    %for i, target_history in enumerate( target_histories ):
                        <%
                            encoded_id = trans.security.encode_id( target_history.id )
                            if encoded_id == target_history_id:
                                selected_text = " selected='selected'"
                            else:
                                selected_text = ""
                            if target_history == current_history:
                                current_history_text = " (current history)"
                            else:
                                current_history_text = ""
                        %>
                        <option value="${encoded_id}"${selected_text}>${i + 1}: ${h.truncate( target_history.name, 30 )}${current_history_text}</option>
                    %endfor
                </select>
                <br/><br/>
                <a style="margin-left: 10px;" href="javascript:void(0);" id="select-multiple">Choose multiple histories</a>
            </div>
            <div id="multiple-destination" style="display: none;">
                %for i, target_history in enumerate( target_histories ):
                    <%
                        encoded_id = trans.security.encode_id( target_history.id )
                        if target_history == current_history:
                            current_history_text = " (current history)"
                        else:
                            current_history_text = ""
                    %>
                    <div class="form-row">
                        <input type="checkbox" name="target_history_ids" id="target_history_${encoded_id}" value="${encoded_id}"/>
                        <label for="target_history_${encoded_id}" style="display: inline; font-weight:normal;">${i + 1}: ${target_history.name}${current_history_text}</label>
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
            <input type="submit" class="primary-button" name="import_datasets_to_histories_button" value="Import library datasets"/>
        </div>
    </form>
</div>
