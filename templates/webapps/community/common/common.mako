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

<%def name="render_readme( readme_text )">
    <% readme_text = readme_text.replace( '\n', '<br/>' ) %>
    <style type="text/css">
        #readme_table{ table-layout:fixed;
                       width:100%;
                       overflow-wrap:normal;
                       overflow:hidden;
                       border:0px; 
                       word-break:keep-all;
                       word-wrap:break-word;
                       line-break:strict; }
    </style>
    <div class="toolForm">
        <div class="toolFormTitle">Repository README file (may contain important installation or license information)</div>
        <div class="toolFormBody">
            <div class="form-row">
                <table id="readme_table">
                    <tr><td>${readme_text}</td></tr>
                </table>
            </div>
        </div>
    </div>
</%def>

<%def name="render_long_description( description_text )">
    <% description_text = description_text.replace( '\n', '<br/>' ) %>
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
