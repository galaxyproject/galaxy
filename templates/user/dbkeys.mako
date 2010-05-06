<%inherit file="/base.mako"/>
<%def name="title()">Custom Database Builds</%def>

<style type="text/css">
    th, td {
        min-width: 100px;
        vertical-align: text-top;
    }
    pre {
        padding: 0;
        margin: 0;
    }
</style>

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

% if message:
    <div class="errormessagelarge">${message}</div>
% elif lines_skipped > 0:
    <div class="warningmessagelarge">Skipped ${lines_skipped} lines that could not be parsed</div>
% endif

<h2>Custom Database/Builds</h2>

<p>You may specify your own database/builds here.</p>

% if dbkeys:
    <table class="colored" cellspacing="0" cellpadding="0">
        <tr class="header">
            <th>Name</th>
            <th>Key</th>
            <th>Number of Chroms</th>
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
<br />
<form action="dbkeys" method="post" enctype="multipart/form-data">
    <div class="toolForm">
        <div class="toolFormTitle">Add a Build</div>
        <div class="toolFormBody">
            <div class="form-row">
                <label for="name">Name (eg: Human Chromosome):</label>
                <input type="text" id="name" name="name" />
            </div>
            <div class="form-row">
                <label for="key">Key (eg: hg18):</label>
                <input type="text" id="key" name="key" />
            </div>
            <div class="form-row">
                <label for="len_file">Chromosome Length file upload (.len file):</label>
                <input type="file" id="len_file" name="len_file" /><br />
                <label for="len_text">Alternatively, paste length info:</label>
                <textarea id="len_text" name="len_text" cols="40" rows="10"></textarea>
            </div>
            
            <div class="form-row"><input type="submit" name="add" value="Submit"/></div>
        </div>
    </div>
</form>