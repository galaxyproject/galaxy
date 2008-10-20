<%inherit file="/base.mako"/>

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
    $('#users_add').click(function() {
        return !$('#out_users option:selected').remove().appendTo('#in_users');
    });
    $('#users_remove').click(function() {
        return !$('#in_users option:selected').remove().appendTo('#out_users');
    });
    $('#groups_add').click(function() {
        return !$('#out_groups option:selected').remove().appendTo('#in_groups');
    });
    $('#groups_remove').click(function() {
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

<div class="toolForm">
    <div class="toolFormTitle">Role '${role.name}'</div>
    <div class="toolFormBody">
        <form name="associate_role_user_group" id="associate_role_user_group" action="${h.url_for( action='role_members_edit', role_id=role.id )}" method="post" >
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    Users associated with '${role.name}'<br/>
                    ${render_select( "in_users", in_users )}<br/>
                    <input type="submit" id="users_remove" value=">>"/>
                </div>
                <div>
                    Users not associated with '${role.name}'<br/>
                    ${render_select( "out_users", out_users )}<br/>
                    <input type="submit" id="users_add" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    Groups associated with '${role.name}'<br/>
                    ${render_select( "in_groups", in_groups )}<br/>
                    <input type="submit" id="groups_remove" value=">>"/>
                </div>
                <div>
                    Groups not associated with '${role.name}'<br/>
                    ${render_select( "out_groups", out_groups )}<br/>
                    <input type="submit" id="groups_add" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="submit" value="Save"/>
            </div>
        </form>
    </div>
</div>
<p/>
