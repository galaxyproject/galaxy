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
        $('#groups_add_button').click(function() {
            return !$('#out_groups option:selected').remove().appendTo('#in_groups');
        });
        $('#groups_remove_button').click(function() {
            return !$('#in_groups option:selected').remove().appendTo('#out_groups');
        });
        $('#users_add_button').click(function() {
            return !$('#out_users option:selected').remove().appendTo('#in_users');
        });
        $('#users_remove_button').click(function() {
            return !$('#in_users option:selected').remove().appendTo('#out_users');
        });
        $('form#associate_role_group_user').submit(function() {
            $('#in_groups option').each(function(i) {
                $(this).attr("selected", "selected");
            });
            $('#in_users option').each(function(i) {
                $(this).attr("selected", "selected");
            });
        });
        //Temporary removal of select2 for inputs -- refactor this later.
        $('select').select2("destroy");
    });
</script>

<%
    from galaxy.web.form_builder import CheckboxField
    create_group_for_role_checkbox = CheckboxField( 'create_group_for_role' )
%>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create Role</div>
    <div class="toolFormBody">
        <form name="associate_role_group_user" id="associate_role_group_user" action="${h.url_for(controller='admin', action='create_role' )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <input  name="name" type="textfield" value="${name}" size=40"/>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <input  name="description" type="textfield" value="${description}" size=40"/>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Groups associated with new role</label>
                    ${render_select( "in_groups", in_groups )}<br/>
                    <input type="submit" id="groups_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Groups not associated with new role</label>
                    ${render_select( "out_groups", out_groups )}<br/>
                    <input type="submit" id="groups_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Users associated with new role</label>
                    ${render_select( "in_users", in_users )}<br/>
                    <input type="submit" id="users_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Users not associated with new role</label>
                    ${render_select( "out_users", out_users )}<br/>
                    <input type="submit" id="users_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                %if create_group_for_role_checked:
                    <% create_group_for_role_checkbox.checked = True %>
                %endif
                ${create_group_for_role_checkbox.get_html()} Create a new group of the same name for this role
            </div>
            <div class="form-row">
                <input type="submit" name="create_role_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
