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
    <div class="toolFormTitle">Set quota default</div>
    <div class="toolFormBody">
        <form name="set_quota_default" id="set_quota_default" action="${h.url_for( action='set_quota_default' )}" method="post" >
            <input name="webapp" type="hidden" value="${webapp}" size=40"/>
            <input name="id" type="hidden" value="${id}"/>
            <div class="form-row">
                <label>Is this quota a default for a class of users (if yes, what type)?</label>
                ${default_selectfield.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Warning: Any users or groups associated with this quota will be disassociated.
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="set_default_quota_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
