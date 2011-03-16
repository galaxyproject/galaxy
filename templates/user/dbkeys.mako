<%!
    def inherit(context):
        if context.get('use_panels'):
            if context.get('webapp'):
                webapp = context.get('webapp')
            else:
                webapp = 'galaxy'
            return '/webapps/%s/base_panels.mako' % webapp
        else:
            return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="title()">Custom Database Builds</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style type="text/css">
        #custom_dbkeys * {
            min-width: 100px;
            vertical-align: text-top;
        }
        pre {
            padding: 0;
            margin: 0;
        }
        ## If page is displayed in panels, pad from edges for readability.
        %if context.get('use_panels'):
        div#center {
            padding: 10px;
        }
        %endif
    </style>
</%def>

<%def name="javascripts()">
   ${parent.javascripts()}
   
    <script type="text/javascript">

    $(function() {
        $(".db_hide").each(function() {
            var pre = $(this);
            pre.hide();
            pre.siblings("span").wrap( "<a href='javascript:void(0);'></a>" ).click( function() {
                pre.toggle();
            });     
        });
    });

    </script>
</%def>

<%def name="center_panel()">
    ${self.body()}
</%def>

<%def name="body()">

    % if message:
        <div class="errormessagelarge">${message}</div>
    % elif lines_skipped > 0:
        <div class="warningmessagelarge">Skipped ${lines_skipped} lines that could not be parsed. (Line was either blank or not 2-column, with 2nd column being an integer)</div>
    % endif
    
    <h2>Custom Database/Builds</h2>

    <p>Current custom builds:</p>

    % if dbkeys:
        <table id="custom_dbkeys" class="colored" cellspacing="0" cellpadding="0">
            <tr class="header">
                <th>Name</th>
                <th>Key</th>
                <th>Number of chroms/contigs</th>
                <th></th>
            </tr>
        % for key, dct in dbkeys.iteritems():
            <tr>
                <td>${dct['name'] | h}</td>
                <td>${key | h}</td>
                <td>
    ##                <span>${len(dct["chroms"])} entries</span>
    ##                <pre id="pre_${key}" class="db_hide">
    ##                    <table cellspacing="0" cellpadding="0">
    ##                        <tr><th>Chrom</th><th>Length</th></tr>
    ##                        % for chrom, chrom_len in dct["chroms"].iteritems():
    ##                            <tr><td>${chrom | h}</td><td>${chrom_len | h}</td></tr>
    ##                        % endfor
    ##                    </table>
    ##                </pre>
                    % if 'count' in dct:
                        ${dct['count']}
                    % endif
                </td>
                <td><form action="dbkeys" method="post"><input type="hidden" name="key" value="${key}" /><input type="submit" name="delete" value="Delete" /></form></td>
            </tr>
        % endfor
        </table>
    % else:
        <p>You currently have no custom builds.</p>
    % endif
    <p>Builds with system-installed len files: <em>${installed_len_files}</em></p>
    <br />
    
    <form action="dbkeys" method="post" enctype="multipart/form-data">
        <div class="toolForm" style="float: left;">
            <div class="toolFormTitle">Add a Custom Build</div>
            
            
            <div class="toolFormBody">
                <div class="form-row">
                    <label for="name">Build Name (eg: Human Chromosome):</label>
                    <input type="text" id="name" name="name" />
                </div>
                <div class="form-row">
                    <label for="key">Build Key (eg: hg18):</label>
                    <input type="text" id="key" name="key" />
                </div>
                <div class="form-row">
                    <label for="len_file">Chromosome Length file upload (.len file):</label>
                    <input type="file" id="len_file" name="len_file" /><br />
                    <label for="len_text">Or paste length info below:</label>
                    <textarea id="len_text" name="len_text" cols="40" rows="10"></textarea>
                </div>
            
                <div class="form-row"><input type="submit" name="add" value="Submit"/></div>
            </div>
        </div>
    </form>
    <div class="infomessagesmall" style="float: left; margin-left: 10px; width: 40%;">
        <h3>Length Format</h3>
        <p>
            The length format is two-column, separated by whitespace, of the form:
            <pre>chrom/contig   length of chrom/contig</pre>
        </p>
        <p>
            For example, the first few entries of <em>mm9.len</em> are as follows:
            <pre>
chr1    197195432
chr2    181748087
chr3    159599783
chr4    155630120
chr5    152537259
            </pre>
        </p>
        
        <p>Trackster uses this information to populate the select box for chrom/contig, and
        to set the maximum basepair of the track browser. You may either upload a .len file
        of this format, or directly enter the information in the box.
        </p>
        
    </div>
</%def>