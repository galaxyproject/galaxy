import $ from "jquery";

export function init_refresh_on_change() {
    console.log("init_refresh_on_change");

    $("select[refresh_on_change='true']")
        .off("change")
        .change(function () {
            var select_field = $(this);
            var select_val = select_field.val();
            var ref_on_change_vals = select_field.attr("refresh_on_change_values");
            if (ref_on_change_vals) {
                ref_on_change_vals = ref_on_change_vals.split(",");
                var last_selected_value = select_field.attr("last_selected_value");
                if (
                    $.inArray(select_val, ref_on_change_vals) === -1 &&
                    $.inArray(last_selected_value, ref_on_change_vals) === -1
                ) {
                    return;
                }
            }
            $(window).trigger("refresh_on_change");
            $(document).trigger("convert_to_values"); // Convert autocomplete text to values
            select_field.get(0).form.submit();
        });

    // checkboxes refresh on change
    $(":checkbox[refresh_on_change='true']")
        .off("click")
        .click(function () {
            var select_field = $(this);
            var select_val = select_field.val();
            var ref_on_change_vals = select_field.attr("refresh_on_change_values");
            if (ref_on_change_vals) {
                ref_on_change_vals = ref_on_change_vals.split(",");
                var last_selected_value = select_field.attr("last_selected_value");
                if (
                    $.inArray(select_val, ref_on_change_vals) === -1 &&
                    $.inArray(last_selected_value, ref_on_change_vals) === -1
                ) {
                    return;
                }
            }
            $(window).trigger("refresh_on_change");
            select_field.get(0).form.submit();
        });

    // Links with confirmation
    $("a[confirm]")
        .off("click")
        .click(function () {
            return confirm($(this).attr("confirm"));
        });
}
