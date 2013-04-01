<%def name="common_misc_javascripts()">
    <script type="text/javascript">
        function checkAllFields( name )
        {
            var chkAll = document.getElementById( 'checkAll' );
            var checks = document.getElementsByTagName( 'input' );
            var boxLength = checks.length;
            var allChecked = false;
            var totalChecked = 0;
            if ( chkAll.checked == true )
            {
                for ( i=0; i < boxLength; i++ )
                {
                    if ( checks[i].name.indexOf( name ) != -1 )
                    {
                       checks[i].checked = true;
                    }
                }
            }
            else
            {
                for ( i=0; i < boxLength; i++ )
                {
                    if ( checks[i].name.indexOf( name ) != -1 )
                    {
                       checks[i].checked = false
                    }
                }
            }
        }
    </script>
</%def>

<%def name="render_star_rating( name, rating, disabled=False )">
    <%
        if disabled:
            disabled_str = ' disabled="disabled"'
        else:
            disabled_str = ''
        html = ''
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
