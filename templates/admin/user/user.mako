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
    $('#groups_add_button').click(function() {
        return !$('#out_groups option:selected').remove().appendTo('#in_groups');
    });
    $('#groups_remove_button').click(function() {
        return !$('#in_groups option:selected').remove().appendTo('#out_groups');
    });
    $('form#associate_user_role_group').submit(function() {
        $('#in_roles option').each(function(i) {
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
    <div class="toolFormTitle">User '${user.email}'</div>
    <div class="toolFormBody">
        <form name="associate_user_role_group" id="associate_user_role_group" action="${h.url_for(controller='admin', action='manage_roles_and_groups_for_user', id=trans.security.encode_id( user.id ) )}" method="post" >
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Roles associated with '${user.email}'</label>
                    ${render_select( "in_roles", in_roles )}<br/>
                    <input type="submit" id="roles_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Roles not associated with '${user.email}'</label>
                    ${render_select( "out_roles", out_roles )}<br/>
                    <input type="submit" id="roles_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Groups associated with '${user.email}'</label>
                    ${render_select( "in_groups", in_groups )}<br/>
                    <input type="submit" id="groups_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Groups not associated with '${user.email}'</label>
                    ${render_select( "out_groups", out_groups )}<br/>
                    <input type="submit" id="groups_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="user_roles_groups_edit_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
