##
## TODO: what is needed is a general template for an 'embedded grid' that
## can be easily subclassed. Importing methods like this template does
## not make it possible to easily subclass templates.
##
<%namespace file="../grid_base.mako" import="*" />

## Need to define title so that it can be overridden by child templates.
<%def name="title()"><h2>${grid.title}</h2></%def>

${self.title()}
${stylesheets()}
${grid_javascripts()}
##
## Load grid label and page links within a modal window.
##
<script type="text/javascript">
    // Handle all label clicks.
    var f = function() {
        $("a.label,.page-link>a").click(function() {
            var parent_body = $(this).parents("div.body");
            if (parent_body.length != 0) {
                parent_body.load($(this).attr("href"));
                return false;
            }
        });            
    };
    // Need to process label URLs when document loaded and when grid changes. 
    $(document).ready(function() {
        f();
        $('#grid-table-body').bind('update', f);
    });
</script>
${render_grid_header( grid, False )}
${render_grid_table( grid, show_item_checkboxes=show_item_checkboxes )}