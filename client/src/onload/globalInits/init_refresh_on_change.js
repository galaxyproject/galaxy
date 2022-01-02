import $ from "jquery";

export function init_refresh_on_change() {
    console.log("init_refresh_on_change");

    document.querySelector("select[refresh_on_change='true']")
        .removeEventListener("change")
        .addEventListener("change", function () {
            var select_field = $(this);
            var select_val = select_field.val();
            var ref_on_change_vals = select_field.attr("refresh_on_change_values");
            if (ref_on_change_vals) {
                ref_on_change_vals = ref_on_change_vals.split(",");
                var last_selected_value = select_field.attr("last_selected_value");
                if (
                    !ref_on_change_vals.includes(select_val) &&
                    !ref_on_change_vals.includes(last_selected_value)
                ) {
                    return;
                }
            }
            window.dispatchEvent(new Event("refresh_on_change"));
            document.dispatchEvent("convert_to_values"); // Convert autocomplete text to values
            select_field.get(0).form.submit();
        }, false);

    // checkboxes refresh on change
    document.querySelector(":checkbox[refresh_on_change='true']")
        .removeEventListener("click")
        .addEventListener("click", function () {
            var select_field = $(this);
            var select_val = select_field.val();
            var ref_on_change_vals = select_field.attr("refresh_on_change_values");
            if (ref_on_change_vals) {
                ref_on_change_vals = ref_on_change_vals.split(",");
                var last_selected_value = select_field.attr("last_selected_value");
                if (
                    !ref_on_change_vals.includes(select_val) &&
                    !ref_on_change_vals.includes(last_selected_value)
                ) {
                    return;
                }
            }
            window.dispatchEvent("refresh_on_change");
            select_field.get(0).form.submit();
        }, false);

    // Links with confirmation
    document.querySelector("a[confirm]")
        .removeEventListener("click")
        .addEventListener("click", function () {
            return confirm($(this).attr("confirm"));
        }, false);
}
