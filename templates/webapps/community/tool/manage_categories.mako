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
    $('#categories_add_button').click(function() {
        return !$('#out_categories option:selected').remove().appendTo('#in_categories');
    });
    $('#categories_remove_button').click(function() {
        return !$('#in_categories option:selected').remove().appendTo('#out_categories');
    });
    $('form#associate_tool_category').submit(function() {
        $('#in_categories option').each(function(i) {
            $(this).attr("selected", "selected");
        });
    });
});
</script>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Tool '${tool.name}'</div>
    <div class="toolFormBody">
        <form name="associate_tool_category" id="associate_tool_category" action="${h.url_for( controller='common', action='manage_categories', id=trans.security.encode_id( tool.id ) )}" method="post" >
            <input  name="cntrller" type="hidden" value="${cntrller}" size=40"/>
            <div class="form-row">
                <div style="float: left; margin-right: 10px;">
                    <label>Categories associated with '${tool.name}'</label>
                    ${render_select( "in_categories", in_categories )}<br/>
                    <input type="submit" id="categories_remove_button" value=">>"/>
                </div>
                <div>
                    <label>Categories not associated with '${tool.name}'</label>
                    ${render_select( "out_categories", out_categories )}<br/>
                    <input type="submit" id="categories_add_button" value="<<"/>
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="manage_categories_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
