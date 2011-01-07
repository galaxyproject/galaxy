<%inherit file="/grid_base.mako"/>

##
## Load grid label links within a modal window.
##
<%def name="javascripts()">
    ${parent.javascripts()}
    ## Needed for adding tracks dynamically:
    ${h.js( "jquery.ui.sortable.slider" )}
    <script type="text/javascript">
        // Handle all label clicks.
        var f = function() {
            $("a.label").click(function() {
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
</%def>