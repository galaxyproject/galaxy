<%inherit file="/base.mako"/>


<%def name="title()">Dataset Display</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        var DATASET_URL = "${h.url_for( controller='/dataset', action='display', dataset_id=trans.security.encode_id( dataset.id ))}";
        var DATASET_COLS = ${dataset.metadata.columns};
        var current_chunk = 0;

        function fillTable(){
            if (current_chunk !== -1){
                var table = $('#content_table');
                $.getJSON(DATASET_URL, {chunk: current_chunk}, function (result) {
                    if (result.ck_data !== ""){
                        var lines = result.ck_data.split('\n');
                        $.each(lines, function(){
                            var line = this;
                            var cells = line.split('\t');
                            /* Check length of cells to ensure this is a complete row. */
                            if (cells.length == DATASET_COLS){
                                table.append('<tr><td>' + cells.join('</td><td>') + '</td></tr>');
                            }
                            else{
                                table.append('<tr><td colspan="'+ DATASET_COLS+ '">' + line + '</td></tr>');
                            }
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
                console.log($(window).scrollTop());
                console.log($(document).height());
                console.log($(window).height());
                // if ($(window).scrollTop() == $(document).height() - $(window).height()){
                if ($(document).height() - $(window).scrollTop() <=  $(window).height()){
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
