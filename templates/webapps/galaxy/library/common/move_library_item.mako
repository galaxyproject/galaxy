<%namespace file="/message.mako" import="render_msg" />
<%inherit file="/base.mako"/>

<%def name="javascripts()">
   ${parent.javascripts()}
   ${h.js("libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging" )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>

<%
    if source_library:
        source_library_id = trans.security.encode_id( source_library.id )
    else:
        source_library_id = ''
    if target_library:
        target_library_id = trans.security.encode_id( target_library.id )
    else:
        target_library_id = ''
%>

%if message:
    ${render_msg( message, status )}
%endif

<b>Move data library items</b>
<br/><br/>
<form name="move_library_item" action="${h.url_for( controller='library_common', action='move_library_item', cntrller=cntrller, item_type=item_type, make_target_current=make_target_current, use_panels=use_panels, show_deleted=show_deleted )}" method="post">
    <div class="toolForm" style="float: left; width: 45%; padding: 0px;">
        <div class="toolFormBody">
            <input type="hidden" name="source_library_id" value="${source_library_id}"/>
            %if target_library:
                <input type="hidden" name="target_library_id" value="${target_library_id}"/>
            %endif
            %if item_type == 'ldda':
                %for move_ldda in move_lddas:
                    <%
                        checked = ""
                        encoded_id = trans.security.encode_id( move_ldda.id )
                        if move_ldda.id in move_ldda_ids:
                            checked = " checked='checked'"
                    %>
                    <div class="form-row">
                        <input type="checkbox" name="item_id" id="dataset_${encoded_id}" value="${encoded_id}" ${checked}/>
                        <label for="dataset_${encoded_id}" style="display: inline;font-weight:normal;">${util.unicodify( move_ldda.name )}</label>
                    </div>
                %endfor
            %elif item_type == 'folder':
                <div class="form-row">
                    <% encoded_id = trans.security.encode_id( move_folder.id ) %>
                    <input type="checkbox" name="item_id" id="folder_${encoded_id}" value="${encoded_id}" checked='checked'/>
                    <label for="folder_${encoded_id}" style="display: inline;font-weight:normal;">${move_folder.name}</label>
                </div>
            %endif
        </div>
    </div>
    <div style="float: left; padding-left: 10px; font-size: 36px;">&rarr;</div>
    <div class="toolForm" style="float: right; width: 45%; padding: 0px;">
        %if target_library:
            <div class="toolFormTitle">Select folder within data library: ${h.truncate( target_library.name, 30 )}</div>
        %else:
            <div class="toolFormTitle">Select a data library</div>
        %endif
        <div class="toolFormBody">
            %if target_library:
                <div class="form-row">
                    %if len( target_folder_id_select_field.options ) >= 1:
                        ${target_folder_id_select_field.get_html()}
                    %else:
                        %if source_library and source_library.id == target_library.id:
                            You are not authorized to move items within the source data library
                        %else:
                            You are not authorized to move items into the selected data library
                        %endif
                    %endif
                    %if source_library: 
                        <br/><br/>
                        %if target_library.id == source_library.id:
                            <a style="margin-left: 10px;" href="${h.url_for( controller='library_common', action='move_library_item', cntrller=cntrller, item_type=item_type, item_id=item_id, source_library_id=source_library_id, make_target_current=False, use_panels=use_panels, show_deleted=show_deleted )}">Choose another data library</a>
                        %else:
                            <a style="margin-left: 10px;" href="${h.url_for( controller='library_common', action='move_library_item', cntrller=cntrller, item_type=item_type, item_id=item_id, source_library_id=source_library_id, make_target_current=True, use_panels=use_panels, show_deleted=show_deleted )}">Choose source data library</a>
                        %endif
                    %elif not target_library_folders:
                        <br/><br/>
                        <a style="margin-left: 10px;" href="${h.url_for( controller='library_common', action='move_library_item', cntrller=cntrller, item_type=item_type, item_id=item_id, source_library_id=source_library_id, make_target_current=False, use_panels=use_panels, show_deleted=show_deleted )}">Choose another data library</a>
                    %endif
                </div>
            %else:
                <div class="form-row">
                    %if len( target_library_id_select_field.options ) > 1:
                        ${target_library_id_select_field.get_html()}
                    %else:
                        You are not authorized to move items to any data libraries
                    %endif
                </div>
            %endif
        </div>
    </div>
    <div style="clear: both"></div>
    <div class="form-row" align="center">
        <input type="submit" class="primary-button" name="move_library_item_button" value="Move"/>
    </div>
</form>
