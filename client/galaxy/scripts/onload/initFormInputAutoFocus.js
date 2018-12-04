import $ from "jquery";

/**
 * Another random DOM manipulation applied globally.
 * Transplanted here from base.mako, js-app.jako
 * TODO: remove and associate with forms that actually use this feature
 * 
 * @param {object} galaxy Galaxy instance
 * @param {object} config Galaxy configuration object
 */
export const initFormInputAutoFocus = (galaxy, config) => {
    console.log("initFormInputAutoFocus");
    if (!config) throw new Error("Missing configuration object");
    
    if (config.form_input_auto_focus) {
        $(function () {
            // Auto Focus on first item on form
            if ($("*:focus").html() == null) {
                $(":input:not([type=hidden]):visible:enabled:first").focus();
            }
        });
    }
}

