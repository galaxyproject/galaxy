<%def name="render_checkbox(checkbox, disabled=False, refresh_on_change=False)">
    <% from galaxy.web.form_builder import CheckboxField %>
    <input type="checkbox" id="${checkbox.name}" name="${checkbox.name}" value="true"
        ${"refresh_on_change='true'" if refresh_on_change else ""}
        ${"checked" if CheckboxField.is_checked(checkbox.value) else ""}
        ${"disabled" if disabled else ""}
    >
</%def>

<%def name="render_select(select)">
    <% from markupsafe import escape %>
    <% from galaxy.util import listify %>
    %if select.display == "checkboxes":
        %for o in select.options:
            <div>
                <% selected = o[1] in listify(select.value) or o[2] %>
                <input type="checkbox" name="${select.name}" value="${escape(o[1])}"
                ${'refresh_on_change="true"' if select.refresh_on_change else ""}"
                ${"checked" if selected else ""} ${"disabled" if disabled else ""}>
                ${escape(o[0])}
            </div>
        %endfor
    %else:
        <select id="${select.field_id}" name="${select.name}"
            ${"multiple" if select.multiple else ""}
            ${'refresh_on_change="true"' if select.refresh_on_change else ""}>
            %for o in select.options:
                <% selected = o[1] in listify(select.value) or o[2] %>
                <option value="${escape(o[1])}" ${"selected" if selected else ""}>${escape(o[0])}</option>
            %endfor
        </select>
    %endif
</%def>

<%def name="common_misc_javascripts()">
    <script type="text/javascript">
        function checkAllFields( chkAll, name )
        {
            var checks = document.getElementsByTagName( 'input' );
            var boxLength = checks.length;
            var allChecked = false;
            var totalChecked = 0;
            if ( chkAll.checked == true )
            {
                for ( i=0; i < boxLength; i++ )
                {
                    if ( checks[ i ].name.indexOf( name ) != -1 )
                    {
                       checks[ i ].checked = true;
                    }
                }
            }
            else
            {
                for ( i=0; i < boxLength; i++ )
                {
                    if ( checks[ i ].name.indexOf( name ) != -1 )
                    {
                       checks[ i ].checked = false;
                    }
                }
            }
        }

        function checkAllRepositoryIdFields()
        {
            var chkAll = document.getElementById( 'checkAll' );
            var name = 'repository_ids';
            checkAllFields( chkAll, name );
        }

        function checkAllInstalledToolDependencyIdFields()
        {
            var chkAll = document.getElementById( 'checkAllInstalled' );
            var name = 'inst_td_ids';
            checkAllFields( chkAll, name );
        }

        function checkAllUninstalledToolDependencyIdFields()
        {
            var chkAll = document.getElementById( 'checkAllUninstalled' );
            var name = 'uninstalled_tool_dependency_ids';
            checkAllFields( chkAll, name );
        }
    </script>
</%def>

<%def name="render_deprecated_repository_dependencies_message( deprecated_repository_dependency_tups )">
    <div class="warningmessage">
        <%
            from tool_shed.util.common_util import parse_repository_dependency_tuple
            msg = '<ul>'
            for deprecated_repository_dependency_tup in deprecated_repository_dependency_tups:
                toolshed, name, owner, changeset_revision, pir, oicct = \
                parse_repository_dependency_tuple( deprecated_repository_dependency_tup )
                msg += '<li>Revision <b>%s</b> of repository <b>%s</b> owned by <b>%s</b></li>' % \
                    ( changeset_revision, name, owner )
            msg += '</ul>'
        %>
        This repository depends upon the following deprecated repositories<br/>
        ${msg}
    </div>
</%def>

<%def name="render_star_rating( name, rating, disabled=False )">
    <%
        if disabled:
            disabled_str = ' disabled="disabled"'
        else:
            disabled_str = ''
        html = ''
        rating = rating or 0
        for index in range( 1, 6 ):
            html += '<input name="%s" type="radio" class="star" value="%s" %s' % ( str( name ), str( index ), disabled_str )
            if rating > ( index - 0.5 ) and rating < ( index + 0.5 ):
                html += ' checked="checked"'
            html += '/>'
    %>
    ${html}
</%def>

<%def name="render_long_description( description_text )">
    <style type="text/css">
        #description_table{ table-layout:fixed;
                            width:100%;
                            overflow-wrap:normal;
                            overflow:hidden;
                            border:0px; 
                            word-break:keep-all;
                            word-wrap:break-word;
                            line-break:strict; }
    </style>
    <div class="form-row">
        <label>Detailed description:</label>
        <table id="description_table">
            <tr><td>${description_text}</td></tr>
        </table>
        <div style="clear: both"></div>
    </div>
</%def>

<%def name="render_multiple_heads_message( heads )">
    <div class="warningmessage">
        <%
            from tool_shed.util.hg_util import get_revision_label_from_ctx
            heads_str = ''
            for ctx in heads:
                heads_str += '%s<br/>' % get_revision_label_from_ctx( ctx, include_date=True )
        %>
        Contact the administrator of this Tool Shed as soon as possible and let them know that
        this repository has the following multiple heads which must be merged.<br/>
        ${heads_str}
    </div>
</%def>

<%def name="render_review_comment( comment_text )">
    <style type="text/css">
        #reviews_table{ table-layout:fixed;
                        width:100%;
                        overflow-wrap:normal;
                        overflow:hidden;
                        border:0px; 
                        word-break:keep-all;
                        word-wrap:break-word;
                        line-break:strict; }
    </style>
    <table id="reviews_table">
        <tr><td>${comment_text}</td></tr>
    </table>
</%def>
