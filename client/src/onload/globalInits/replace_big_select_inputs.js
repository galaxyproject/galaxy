// Transplanted from "onload.js"

import $ from "jquery";

function refresh_select2(element) {
    var select_elt = $(element);
    var options = {
        placeholder: "Click to select",
        closeOnSelect: !select_elt.is("[MULTIPLE]"),
        dropdownAutoWidth: true,
        containerCssClass: "select2-minwidth",
    };
    return element.select2(options);
}

// Replace select box with a text input box + autocomplete.
export function replace_big_select_inputs(min_length, max_length, select_elts) {
    console.log("replace_big_select_inputs");

    // To do replace, the select2 plugin must be loaded.
    if (!$.fn.select2) {
        console.warn("No select 2");
        return;
    }

    // Set default for min_length and max_length
    if (min_length === undefined) {
        min_length = 20;
    }
    if (max_length === undefined) {
        max_length = 3000;
    }

    select_elts = select_elts || $("select");

    select_elts.each(function () {
        var select_elt = $(this).not("[multiple]");
        // Make sure that options is within range.
        var num_options = select_elt.find("option").length;
        if (num_options < min_length || num_options > max_length) {
            return;
        }

        if (select_elt.hasClass("no-autocomplete")) {
            return;
        }

        /* Replaced jQuery.autocomplete with select2, notes:
         * - multiple selects are supported
         * - the original element is updated with the value, convert_to_values should not be needed
         * - events are fired when updating the original element, so refresh_on_change should just work
         *
         * - should we still sort dbkey fields here?
         */
        refresh_select2(select_elt);
    });
}
