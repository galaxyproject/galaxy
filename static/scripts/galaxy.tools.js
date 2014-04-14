// dependencies
define([ "mvc/tools" ], function( Tools ) {

    var checkUncheckAll = function( name, check ) {
        $("input[name='" + name + "'][type='checkbox']").attr('checked', !!check);
    }

    // Inserts the Select All / Unselect All buttons for checkboxes
    $("div.checkUncheckAllPlaceholder").each( function() {
        var check_name = $(this).attr("checkbox_name");
        select_link = $("<a class='action-button'></a>").text("Select All").click(function() {
           checkUncheckAll(check_name, true);
        });
        unselect_link = $("<a class='action-button'></a>").text("Unselect All").click(function() {
           checkUncheckAll(check_name, false);
        });
        $(this).append(select_link).append(" ").append(unselect_link);
    });

});
