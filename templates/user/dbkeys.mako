<%!
    def inherit(context):
        if context.get('use_panels'):
            return '/webapps/galaxy/base_panels.mako'
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
        div.def_tab {
            float: left;
            padding: 0.2em 0.5em;
            background-color: white;
        }
        div.def_tab.active {
            background-color: #CCF;
            border: solid 1px #66A;
        }
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
        $("#installed_builds").hide();
        $("#show_installed_builds").click(function() {
            $("#installed_builds").show();
        });
        
        // Set up behavior for build definition tab controls.
        $("div.def_tab > a").each(function() {
            $(this).click(function() {
                var tab_id = $(this).attr("id");

                // Hide all build inputs, help.
                $("div.build_definition").children(":input").hide();
                $(".infomessagesmall > div").hide();
                
                // Show input item, help corresponding to tab id.
                $("#" + tab_id + "_input").show();
                $("." + tab_id + "_help").show();
                
                // Update tabs.
                $("div.def_tab").removeClass("active");
                $(this).parent().addClass("active");
            });
        });
        
        ## If there are fasta HDAs available, show fasta tab; otherwise show len file tab.
        // Set starting tab.
        % if fasta_hdas.first():
            $("#fasta").click();
        % else:
            $("#len_file").click();
        % endif
        
        // Before submit, remove inputs not associated with the active tab.
        $("#submit").click(function() {
            var id = $(this).parents("form").find(".active > a").attr("id");
            $("div.build_definition").children(":input").each(function() {
                if ( $(this).attr("id") !== (id + "_input")  ) {
                    $(this).remove();
                }
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

    <h3>Current Custom Builds:</h3>

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
                    % else:
                        Processing
                    % endif
                </td>
                <td><form action="dbkeys" method="post"><input type="hidden" name="key" value="${key}" /><input type="submit" name="delete" value="Delete" /></form></td>
            </tr>
        % endfor
        </table>
    % else:
        <p>You currently have no custom builds.</p>
    % endif
    
    <p>
        <a id="show_installed_builds" href="javascript:void(0);">Show loaded, system-installed builds</a>
        <blockquote id="installed_builds">${installed_len_files}</blockquote>
    </p>
    
    <hr />
    <h3>Add a Custom Build</h3>
    <form action="dbkeys" method="post" enctype="multipart/form-data">
        ## Include hidden param for panels:
        %if use_panels:
            <input type="hidden" name="use_panels" value="True">
        %endif
        ## Custom build via fasta in history.
        <div class="toolForm" style="float: left;">
            <div class="toolFormTitle">New Build</div>
            <div class="toolFormBody">
                <div class="form-row">
                    <label for="name">Name (eg: Hamster):</label>
                    <input type="text" id="name" name="name" />
                </div>
                <div class="form-row">
                    <label for="key">Key (eg: hamster_v1):</label>
                    <input type="text" id="key" name="key" />
                </div>
                <div class="form-row build_definition">
                    <label>Definition:</label>
                    <div class="def_tab">
                        <a id="fasta" href="javascript:void(0)">FASTA</a>
                    </div>
                    <div class="def_tab">
                        <a id="len_file" href="javascript:void(0)">Len File</a>
                    </div>
                    <div class="def_tab">
                        <a id="len_entry" href="javascript:void(0)">Len Entry</a>
                    </div>
                    <div style="clear: both; padding-bottom: 0.5em"></div>
                    <select id="fasta_input" name="dataset_id">
                    %for dataset in fasta_hdas:
                        <option value="${trans.security.encode_id( dataset.id )}">${dataset.hid}: ${dataset.name}</option>
                    %endfor
                    </select>
                    <input type="file" id="len_file_input" name="len_file" /></input>
                    <textarea id="len_entry_input" name="len_text" cols="30" rows="8"></textarea>
                </div>            
                <div class="form-row"><input id="submit" type="submit" name="add" value="Submit"/></div>
            </div>
        </div>
    </form>
    <div class="infomessagesmall" style="float: left; margin-left: 10px; width: 40%;">
        <div class="fasta_help">
            <h3>FASTA format</h3>
            <p>
                This is a multi-fasta file from your current history that provides the genome 
                sequences for each chromosome/contig in your build.
            </p>
            
            <p>
                Here is a snippet from an example multi-fasta file:
                <pre>
    >chr1
    ATTATATATAAGACCACAGAGAGAATATTTTGCCCGG...
    >chr2
    GGCGGCCGCGGCGATATAGAACTACTCATTATATATA...
    ...
                </pre>
            </p>
        </div>
        <div class="len_file_help len_entry_help">
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
            of this format (Len File option), or directly enter the information into the box 
            (Len Entry option).</p>
        </div>
    </div>
</%def>
