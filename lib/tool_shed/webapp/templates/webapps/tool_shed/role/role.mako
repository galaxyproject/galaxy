<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

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
    $('#repositories_add_button').click(function() {
        return !$('#out_repositories option:selected').remove().appendTo('#in_repositories');
    });
    $('#repositories_remove_button').click(function() {
        return !$('#in_repositories option:selected').remove().appendTo('#out_repositories');
    });
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
    $('form#manage_role_associations').submit(function() {
        $('#in_repositories option').each(function(i) {
            $(this).attr("selected", "selected");
        });
        $('#in_users option').each(function(i) {
            $(this).attr("selected", "selected");
        });
        $('#in_groups option').each(function(i) {
            $(this).attr("selected", "selected");
        });
    });
});
</script>

<%
    if trans.user_is_admin and in_admin_controller:
        render_for_admin = True
    else:
        render_for_admin = False
%>

%if not render_for_admin:
    ${render_tool_shed_repository_actions( repository, metadata=metadata, changeset_revision=changeset_revision )}
%endif

%if message:
    ${render_msg( message, status )}
%endif

<div class="warningmessage">
    <b>${role.name}</b> is the administrator role for the repository <b>${repository.name}</b> owned by 
    <b>${repository.user.username}</b>.  ${role.description}
</div>

<div class="toolForm">
    <div class="toolFormTitle">Manage users and groups associated with role <b>${role.name}</b></div>
    <div class="toolFormBody">
        % if not render_for_admin:
            <div class="form-row">
                <label>Repository name:</label>
                ${repository.name}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Repository owner:</label>
                ${repository.user.username}
                <div style="clear: both"></div>
            </div>
        %endif
        <%
            if render_for_admin:
                controller_module = 'admin'
                controller_method = 'manage_role_associations'
                id_param = trans.security.encode_id( role.id )
            else:
                controller_module = 'repository'
                controller_method = 'manage_repository_admins'
                id_param = trans.security.encode_id( repository.id )
        %>
        <form name="manage_role_associations" id="manage_role_associations" action="${h.url_for( controller=controller_module, action=controller_method, id=id_param )}" method="post" >
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Users associated with '${role.name}'</label>
                    ${render_select( "in_users", in_users )}<br/>
                    <input type="submit" id="users_remove_button" value=">>"/>
                    <div style="clear: both"></div>
                </div>
                <div>
                    <label>Users not associated with '${role.name}'</label>
                    ${render_select( "out_users", out_users )}<br/>
                    <input type="submit" id="users_add_button" value="<<"/>
                    <div style="clear: both"></div>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Groups associated with '${role.name}'</label>
                    ${render_select( "in_groups", in_groups )}<br/>
                    <input type="submit" id="groups_remove_button" value=">>"/>
                    <div style="clear: both"></div>
                </div>
                <div>
                    <label>Groups not associated with '${role.name}'</label>
                    ${render_select( "out_groups", out_groups )}<br/>
                    <input type="submit" id="groups_add_button" value="<<"/>
                    <div style="clear: both"></div>
                </div>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" name="manage_role_associations_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
