##
## TODO: what is needed is a general template for an 'embedded grid' that
## can be easily subclassed. Importing methods like this template does
## not make it possible to easily subclass templates.
##
<%namespace file="../grid_base.mako" import="*" />

${stylesheets()}
${grid_javascripts()}

<%def name="select_header()">
    <script type="text/javascript">
        // Load all grid URLs into modal-body element so that
        // grid + links stays embedded.
        var load_urls_into_modal_body = function() {
            $(".addtracktab, #grid-table a").click(function() {
                var modal_body = $(".modal-body");
                if (modal_body.length !== 0) {
                    modal_body.load($(this).attr("href"));
                    return false;
                }
            });
        };
        // Need to process label URLs when document loaded and when grid changes. 
        $(document).ready(function() {
            load_urls_into_modal_body();
        });
    </script>
    <style>
        .dialog-box .body {
            overflow-x: hidden;
        }
        .addtracktab {
            margin: 0px 5px;
            padding: 5px;
            display: block;
            width: 35%;
            text-align: center;
            float: left;
            background-color: #ccc;
            border: 1px solid #ccc;
            border-bottom: 0px;
            -webkit-border-top-left-radius: 10px;
            -webkit-border-top-right-radius: 10px;
            -moz-border-radius-topleft: 10px;
            -moz-border-radius-topright: 10px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        }
        .activetab {
            border: 1px solid #aaa;
            border-bottom: 0px;
            background-color: white;
            margin-bottom: -2px;
        }
        .divider {
            clear: both;
            border-top: 1px solid #aaa;
            margin-bottom: 5px;
        }
    
    </style>

    <% histories_active = data_libraries_active = "" %>
    %if getattr(grid, "datasets_param", None):
        %if grid.datasets_param == "f-history":
            <% histories_active = " activetab" %>
        %else:
            <% data_libraries_active = " activetab" %>
        %endif
    %endif
    ## Add filter parameters manually because they include a hyphen and hence cannot be 
    ## added as key words.
    <% 
        dbkey = '?'
        if cur_filter_dict:
            dbkey = cur_filter_dict.get( 'dbkey', '?' ) 
    %>
    <a class="addtracktab${histories_active}" href="${h.url_for(controller='visualization', action='list_histories')}?f-dbkey=${dbkey}">Histories</a>
    <a class="addtracktab${data_libraries_active}" href="${h.url_for(controller='visualization', action='list_libraries' )}">Data Libraries</a>
    <div class="divider"></div>
</%def>

${select_header()}
## Need to define title so that it can be overridden by child templates.
<%def name="title()"></%def>

${self.title()}

${render_grid_header( grid, False )}
${render_grid_table( grid, show_item_checkboxes=show_item_checkboxes )}

