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
        // Handle all label clicks.
        var f = function() {
            $(".addtracktab, #grid-table a").click(function() {
                var parent_body = $(".divider").parent();
                if (parent_body.length !== 0) {
                    parent_body.load($(this).attr("href"));
                    f();
                    return false;
                }
            });
        };
        // Need to process label URLs when document loaded and when grid changes. 
        $(document).ready(function() {
            f();
            // $('#grid-table-body').bind('update', f);
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
    <a class="addtracktab${histories_active}" href="${h.url_for( action='list_histories' )}">Histories</a>
    <a class="addtracktab${data_libraries_active}" href="${h.url_for( action='list_libraries' )}">Data Libraries</a>
    <div class="divider"></div>
</%def>

${select_header()}
## Need to define title so that it can be overridden by child templates.
<%def name="title()"></%def>

${self.title()}

${render_grid_header( grid, False )}
${render_grid_table( grid, show_item_checkboxes=show_item_checkboxes )}

