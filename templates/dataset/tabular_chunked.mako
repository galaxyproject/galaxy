<%inherit file="/base.mako"/>


<%def name="title()">Dataset Display</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        var DATASET_URL   = "${h.url_for( controller='/dataset', action='display', dataset_id=trans.security.encode_id( dataset.id ))}";
        var COLUMN_NUMBER  = ${column_number};
        var COLUMN_TYPES = ${column_types};
        var COLUMN_NAMES = ${column_names};

        var chunk = ${chunk};
        var current_chunk = 0;

        function renderCell(cell_contents, index, colspan){
            if (colspan !== undefined){
                return $('<td>').attr('colspan', colspan).addClass('stringalign').text(cell_contents);
            }
            else if (COLUMN_TYPES[index] == 'str'){
                /* Left align all str columns, right align the rest */
                return $('<td>').addClass('stringalign').text(cell_contents);;
            }
            else{
                return $('<td>').text(cell_contents);
            }
        }

        function renderRow(line){
            /* Check length of cells to ensure this is a complete row. */
            var cells = line.split('\t');
            var row = $('<tr>');
            if (cells.length == COLUMN_NUMBER){
                $.each(cells, function(index, cell_contents){
                    row.append(renderCell(cell_contents, index));
                });
            }
            else if(cells.length > COLUMN_NUMBER){
                /* SAM file or like format with optional metadata included */
                $.each(cells.slice(0, COLUMN_NUMBER -1), function(index, cell_contents){
                    row.append(renderCell(cell_contents, index));
                });
                row.append(renderCell(cells.slice(COLUMN_NUMBER -1).join('\t'), COLUMN_NUMBER-1));
            }
            else if(COLUMN_NUMBER > 5 && cells.length == COLUMN_NUMBER - 1 ){
                /* SAM file or like format with optional metadata missing */
                $.each(cells, function(index, cell_contents){
                    row.append(renderCell(cell_contents, index));
                });
                row.append($('<td>'));
            }
            else{
                /* Comment line, just return the one cell*/
                row.append(renderCell(line, 0, COLUMN_NUMBER));
            }
            return row;
        }

        function renderChunk(chunk){
            var table = $('#content_table');
            if (chunk.ck_data == ""){
                current_chunk = -1;
            }
            else if(chunk.ck_index === current_chunk + 1){
                if (current_chunk === 0 && COLUMN_NAMES){
                    table.append('<tr><th>' + COLUMN_NAMES.join('</th><th>') + '</th></tr>');
                }
                var lines = chunk.ck_data.split('\n');
                $.each(lines, function(index, line){
                    table.append(renderRow(line));
                });
                current_chunk = chunk.ck_index;
            }
        }

        $(document).ready(function(){
            renderChunk(chunk);
            $(window).scroll(function(){
                if ($(window).scrollTop() == $(document).height() - $(window).height()){
                    if (current_chunk !== -1){
                        $.getJSON(DATASET_URL,
                                  {chunk: current_chunk},
                                  function(result){renderChunk(result)});
                    }
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
