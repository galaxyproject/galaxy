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
    <select name="${name}" id="${name}" style="min-width: 250px; height: 150px;" multiple>
        %for option in options:
            <option value="${option[0]}">${option[1]}</option>
        %endfor
    </select>
</%def>

<script type="text/javascript">
$().ready(function() {  
    $('#roles_add_button').click(function() {
        return !$('#out_roles option:selected').remove().appendTo('#in_roles');
    });
    $('#roles_remove_button').click(function() {
        return !$('#in_roles option:selected').remove().appendTo('#out_roles');
    });
    $('#users_add_button').click(function() {
        return !$('#out_users option:selected').remove().appendTo('#in_users');
    });
    $('#users_remove_button').click(function() {
        return !$('#in_users option:selected').remove().appendTo('#out_users');
    });
    $('form#associate_group_role_user').submit(function() {
        $('#in_roles option').each(function(i) {
            $(this).attr("selected", "selected");
        });
        $('#in_users option').each(function(i) {
            $(this).attr("selected", "selected");
        });
    });
});
</script>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Group '${group.name}'</div>
    <div class="toolFormBody">
        <form name="associate_group_role_user" id="associate_group_role_user" action="${h.url_for(controller='admin', action='manage_users_and_roles_for_group', id=trans.security.encode_id( group.id ) )}" method="post" >
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Roles associated with '${group.name}'</label>
                    ${render_select( "in_roles", in_roles )}<br/>
                    <input type="submit" id="roles_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Roles not associated with '${group.name}'</label>
                    ${render_select( "out_roles", out_roles )}<br/>
                    <input type="submit" id="roles_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Users associated with '${group.name}'</label>
                    ${render_select( "in_users", in_users )}<br/>
                    <input type="submit" id="users_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Users not associated with '${group.name}'</label>
                    ${render_select( "out_users", out_users )}<br/>
                    <input type="submit" id="users_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="group_roles_users_edit_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
