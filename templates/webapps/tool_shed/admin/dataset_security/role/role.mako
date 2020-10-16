<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        $(function(){
            $("input:text:first").focus();
        })
    </script>
</%def>

<%def name="render_select( name, options )">
    <select name="${name|h}" id="${name|h}" style="min-width: 250px; height: 150px;" multiple>
        %for option in options:
            <option value="${option[0]|h}">${option[1]|h}</option>
        %endfor
    </select>
</%def>

<script type="text/javascript">
$().ready(function() {  
    $('#users_add_button').click(function() {
        return !$('#out_users option:selected').remove().appendTo('#in_users');
    });
    $('#users_remove_button').click(function() {
        return !$('#in_users option:selected').remove().appendTo('#out_users');
    });
    $('#groups_add_button').click(function() {
        return !$('#out_groups option:selected').remove().appendTo('#in_groups');
    });
    $('#groups_remove_button').click(function() {
        return !$('#in_groups option:selected').remove().appendTo('#out_groups');
    });
    $('form#associate_role_user_group').submit(function() {
        $('#in_users option').each(function(i) {
            $(this).attr("selected", "selected");
        });
        $('#in_groups option').each(function(i) {
            $(this).attr("selected", "selected");
        });
    });
});
</script>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Role '${role.name|h}'</div>
    <div class="toolFormBody">
        <form name="associate_role_user_group" id="associate_role_user_group" action="${h.url_for(controller='admin', action='manage_users_and_groups_for_role', id=trans.security.encode_id( role.id ) )}" method="post" >
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Users associated with '${role.name|h}'</label>
                    ${render_select( "in_users", in_users )}<br/>
                    <input type="submit" id="users_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Users not associated with '${role.name|h}'</label>
                    ${render_select( "out_users", out_users )}<br/>
                    <input type="submit" id="users_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Groups associated with '${role.name|h}'</label>
                    ${render_select( "in_groups", in_groups )}<br/>
                    <input type="submit" id="groups_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Groups not associated with '${role.name|h}'</label>
                    ${render_select( "out_groups", out_groups )}<br/>
                    <input type="submit" id="groups_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="role_members_edit_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
<br clear="left"/>
<br/>
%if len( library_dataset_actions ) > 0:
    <h3>Data library datasets associated with role '${role.name|h}'</h3>
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr>
            <td>
                <ul>
                    %for ctr, library, in enumerate( library_dataset_actions.keys() ):
                        <li>
                            <img src="${h.url_for( '/static/images/silk/book_open.png' )}" class="rowIcon"/>
                            ${library.name|h}
                            <ul>
                                %for folder_path, permissions in library_dataset_actions[ library ].items():
                                    <li>
                                        <img src="/static/images/silk/folder_page.png" class="rowIcon"/>
                                        ${folder_path|h}
                                        <ul>
                                            % for permission in permissions:
                                                <ul>
                                                    <li>${permission|h}</li>
                                                </ul>
                                            %endfor
                                        </ul>
                                    </li>
                                %endfor
                            </ul>
                        </li>
                    %endfor
                </ul>
            </td>
        </tr>
    </table>
%endif
