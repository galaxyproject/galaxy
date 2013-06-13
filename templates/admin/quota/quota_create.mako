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
        $('form#associate_quota_group_user').submit(function() {
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
    from galaxy.web.form_builder import SelectField
    operation_selectfield = SelectField( 'operation' )
    for op in ( '=', '+', '-' ):
        selected = op == operation
        operation_selectfield.add_option( op, op, selected )
    default_selectfield = SelectField( 'default' )
    selected = 'no' == default
    default_selectfield.add_option( 'No', 'no', selected )
    for typ in trans.app.model.DefaultQuotaAssociation.types.__dict__.values():
        selected = typ == default
        default_selectfield.add_option( 'Yes, ' + typ, typ, selected )
%>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create quota</div>
    <div class="toolFormBody">
        <form name="associate_quota_group_user" id="associate_quota_group_user" action="${h.url_for(controller='admin', action='create_quota' )}" method="post" >
            <div class="form-row">
                <label>Name:</label>
                <input  name="name" type="textfield" value="${name}" size=40"/>
            </div>
            <div class="form-row">
                <label>Description:</label>
                <input  name="description" type="textfield" value="${description}" size=40"/>
            </div>
            <div class="form-row">
                <label>Amount</label>
                <input  name="amount" type="textfield" value="${amount}" size=40"/>
                <div class="toolParamHelp" style="clear: both;">
                    Examples: "10000MB", "99 gb", "0.2T", "unlimited"
                </div>
            </div>
            <div class="form-row">
                <label>Assign, increase by amount, or decrease by amount?</label>
                ${operation_selectfield.get_html()}
            </div>
            <div class="form-row">
                <label>Is this quota a default for a class of users (if yes, what type)?</label>
                ${default_selectfield.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Warning: Any user or group associations selected below will be ignored if this quota is used as a default.
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Users associated with new quota</label>
                    ${render_select( "in_users", in_users )}<br/>
                    <input type="submit" id="users_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Users not associated with new quota</label>
                    ${render_select( "out_users", out_users )}<br/>
                    <input type="submit" id="users_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Groups associated with new quota</label>
                    ${render_select( "in_groups", in_groups )}<br/>
                    <input type="submit" id="groups_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Groups not associated with new quota</label>
                    ${render_select( "out_groups", out_groups )}<br/>
                    <input type="submit" id="groups_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="create_quota_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
