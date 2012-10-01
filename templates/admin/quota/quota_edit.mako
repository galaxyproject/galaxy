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

<%
    from galaxy.web.form_builder import SelectField
    operation_selectfield = SelectField( 'operation' )
    for op in ( '=', '+', '-' ):
        selected = op == operation
        operation_selectfield.add_option( op, op, selected )
%>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Change quota amount</div>
    <div class="toolFormBody">
        <form name="library" action="${h.url_for( controller='admin', action='edit_quota' )}" method="post" >
            <input name="id" type="hidden" value="${id}"/>
            <div class="form-row">
                <label>Amount</label>
                <input  name="amount" type="textfield" value="${display_amount}" size=40"/>
                <div class="toolParamHelp" style="clear: both;">
                    Examples: "10000MB", "99 gb", "0.2T", "unlimited"
                </div>
            </div>
            <div class="form-row">
                <label>Assign, increase by amount, or decrease by amount?</label>
                ${operation_selectfield.get_html()}
            </div>
            <div class="form-row">
                <input type="submit" name="edit_quota_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
