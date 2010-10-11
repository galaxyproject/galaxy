<%def name="custom_javascripts()">
    <script type="text/javascript">
        $("#select-dataset-action-button").bind( "click", function(e) {
            $.ajax({
                url: "${h.url_for( controller='requests_admin', action='remote_file_browser' )}",
                data: {id: 6},
                error: function() { alert( "Couldn't create new browser" ) },
                success: function(form_html) {
                    show_modal("Select file", form_html, {
                        "Cancel": function() { window.location = "${h.url_for( controller='requests_admin', action='browse_requests' )}"; },
                        "Continue": function() { $(document).trigger("convert_dbkeys"); continue_fn(); }
                    });
                    $("#new-title").focus();
                    replace_big_select_inputs();
                }
            });
        }
    </script>
</%def>

<%def name="javascripts()">
   ${h.js( "galaxy.base", "galaxy.panels", "json2", "jquery", "jquery.event.drag", "jquery.autocomplete", "jquery.mousewheel", "trackster", "ui.core", "ui.sortable" )}   
   ${self.custom_javascripts()}
   ${parent.javascripts()}
</%def>

<%inherit file="/grid_base.mako"/>
