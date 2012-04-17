<%inherit file="/base.mako"/>


<%def name="title()">Dataset Display</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">

        var DATASET_URL   = "${h.url_for( controller='/dataset', action='display', dataset_id=trans.security.encode_id( dataset.id ))}";
        var DATASET_COLS  = ${dataset.metadata.columns};
        var DATASET_TYPES = ${dataset.metadata.column_types};

        var current_chunk = 0;

        function renderCell(cell_contents, index, colspan){
            if (colspan !== undefined){
                return '<td colspan="'+ colspan + '" class="stringalign">' + cell_contents + '</td>';
            }
            else if (DATASET_TYPES[index] == 'str'){
                /* Left align all str columns, right align the rest */
                return '<td class="stringalign">'+ cell_contents + '</td>';
            }
            else{
                return '<td>'+ cell_contents + '</td>';
            }
        }

        function renderRow(line){
            /* Check length of cells to ensure this is a complete row. */
            var cells = line.split('\t');
            var rowstr = '<tr>';
            if (cells.length == DATASET_COLS){
                $.each(cells, function(index, cell_contents){
                    rowstr += renderCell(cell_contents, index);
                });
            }
            else if(cells.length > DATASET_COLS){
                /* SAM file or like format with optional metadata included */
                $.each(cells.slice(0, DATASET_COLS -1), function(index, cell_contents){
                    rowstr += renderCell(cell_contents, index);
                });
                rowstr += renderCell(cells.slice(DATASET_COLS -1).join('\t'), DATASET_COLS-1);
            }
            else if(DATASET_COLS > 5 && cells.length == DATASET_COLS - 1 ){
                /* SAM file or like format with optional metadata missing */
                $.each(cells, function(index, cell_contents){
                    rowstr += renderCell(cell_contents, index);
                });
                rowstr += '<td></td>';
            }
            else{
                /* Comment line, just return the one cell*/
                rowstr += renderCell(line, 0, DATASET_COLS);
            }
            rowstr += '</tr>';
            return rowstr;
        }

        function fillTable(){
            if (current_chunk !== -1){
                var table = $('#content_table');
                $.getJSON(DATASET_URL, {chunk: current_chunk}, function (result) {
                    if (result.ck_data !== ""){
                        var lines = result.ck_data.split('\n');
                        $.each(lines, function(index, line){
                            table.append(renderRow(line));
                        });
                        current_chunk = result.ck_index;
                    }
                    else {
                        current_chunk = -1;
                    }
                });
            }
        }

        $(document).ready(function(){
            fillTable();
            $(window).scroll(function(){
                if ($(window).scrollTop() == $(document).height() - $(window).height()){
                    fillTable();
                }
            });
        $('#loading_indicator').ajaxStart(function(){
           $(this).show();
        }).ajaxStop(function(){
           $(this).hide();
        });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<div id="loading_indicator" ></div>
<table id="content_table" cellpadding="0">
</table>
