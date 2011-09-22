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
    $('form#associate_quota_user_group').submit(function() {
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
    <div class="toolFormTitle">Quota '${name}'</div>
    <div class="toolFormBody">
        <form name="associate_quota_user_group" id="associate_quota_user_group" action="${h.url_for( action='manage_users_and_groups_for_quota', id=id )}" method="post" >
            <input  name="webapp" type="hidden" value="${webapp}" size=40"/>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Users associated with '${name}'</label>
                    ${render_select( "in_users", in_users )}<br/>
                    <input type="submit" id="users_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Users not associated with '${name}'</label>
                    ${render_select( "out_users", out_users )}<br/>
                    <input type="submit" id="users_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Groups associated with '${name}'</label>
                    ${render_select( "in_groups", in_groups )}<br/>
                    <input type="submit" id="groups_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Groups not associated with '${name}'</label>
                    ${render_select( "out_groups", out_groups )}<br/>
                    <input type="submit" id="groups_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="quota_members_edit_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
