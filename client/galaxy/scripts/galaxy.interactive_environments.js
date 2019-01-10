/* global $ */
/* global toastr */
// TODO: this file is transpiled and used directly without bundling; fix imports when that is no longer the case.
/**
 * Internal function to remove content from the main area and add the notebook.
 * Not idempotent
 * TODO: This isn't just internal, some notebooks are calling it?
 */
export function append_notebook(url) {
    clear_main_area();
    $("#main").append(
        `<iframe frameBorder="0" seamless="seamless" style="width: 100%; height: 100%; overflow:hidden;" scrolling="no" src="${url}"></iframe>`
    );
}

export function clear_main_area() {
    $("#spinner").remove();
    $("#main")
        .children()
        .remove();
}

export function display_spinner() {
    $("#main").append(`<div id="ie-loading-spinner"></div>`);
}

/* Create a spin_state object used by spin() and spin_again() */
export function make_spin_state(
    type,
    ajax_timeout_init,
    ajax_timeout_max,
    ajax_timeout_step,
    sleep_init,
    sleep_max,
    sleep_step,
    log_attempts
) {
    var s = {
        type: typeof type !== "undefined" ? type : "GIE spin",
        ajax_timeout: typeof ajax_timeout_init !== "undefined" ? ajax_timeout_init : 2000,
        ajax_timeout_max: typeof ajax_timeout_max !== "undefined" ? ajax_timeout_max : 16000,
        ajax_timeout_step: typeof ajax_timeout_step !== "undefined" ? ajax_timeout_step : 500,
        sleep: typeof sleep_init !== "undefined" ? sleep_init : 500,
        sleep_max: typeof sleep_max !== "undefined" ? sleep_max : 8000,
        sleep_step: typeof sleep_step !== "undefined" ? sleep_step : 100,
        log_attempts: typeof log_attempts !== "undefined" ? log_attempts : true,
        count: 0
    };
    return s;
}

/* Log/display an error when spinning fails. */
export function spin_error(console_msg, user_msg, clear) {
    console.log(console_msg);
    if (clear) clear_main_area();
    if (typeof user_msg == "string") {
        toastr.clear();
        toastr.error(user_msg, "Error", {
            closeButton: true,
            timeOut: 0,
            extendedTimeOut: 0,
            tapToDismiss: false
        });
    }
}

/* Increase sleep time and spin again. */
function spin_again(spin_state) {
    if (spin_state.sleep < spin_state.sleep_max) {
        spin_state.sleep += spin_state.sleep_step;
    }
    if (spin_state.log_attempts) {
        console.log(
            `${spin_state.type} request ${spin_state.count} request timeout ${
                spin_state.ajax_timeout
            }ms sleeping ${spin_state.sleep / 1000}s`
        );
    }
    window.setTimeout(spin_state.spinner, spin_state.sleep);
}

/*
 * Spin on a URL as long as it times out, otherwise, call the provided success or error callback. If the callback
 * returns `true`, the condition is considered "resolved" and spinning stops. Otherwise, continue spinning, increasing
 * AJAX timeouts and/or sleep values as configured in the spin_state.
 */
export function spin(url, bool_response, success_callback, timeout_callback, error_callback, spin_state) {
    var spinner = () => {
        var ajax_params = {
            url: url,
            xhrFields: {
                withCredentials: true
            },
            type: "GET",
            timeout: spin_state.ajax_timeout,
            success: function(data, status, jqxhr) {
                if (!success_callback(data, status, jqxhr)) {
                    spin_state.count++;
                    spin_again(spin_state);
                }
            },
            error: function(jqxhr, status, error) {
                if (status == "timeout") {
                    if (spin_state.ajax_timeout < spin_state.ajax_timeout_max) {
                        spin_state.ajax_timeout += spin_state.ajax_timeout_step;
                    }
                    spin_state.count++;
                    if (!timeout_callback(jqxhr, status, error)) spin_again(spin_state);
                } else {
                    spin_state.count++;
                    if (!error_callback(jqxhr, status, error)) spin_again(spin_state);
                }
            }
        };
        if (bool_response) ajax_params["dataType"] = "json";
        $.ajax(ajax_params);
    };
    console.log(`Setting up new spinner for ${spin_state.type} on ${url}`);
    spin_state.spinner = spinner;
    window.setTimeout(spinner, spin_state.sleep);
}

/*
 * Spin on a URL forever until there is an acceptable response.
 * @param {String} url: URL to test response of. Must return a 200 (302->200 is OK).
 * @param {Boolean} bool_response: If set to `true`, do not stop spinning until the response is `true`. Otherwise, stop
 *     as soon as a successful response is received.
 */
function spin_until(url, bool_response, messages, success_callback, spin_state) {
    var warn_at = 40; // ~2 mins
    var message_once = (message, spin_state) => {
        if (spin_state.count == 1) {
            display_spinner();
            toastr.info(message, null, {
                closeButton: true,
                timeOut: 0,
                extendedTimeOut: 0,
                tapToDismiss: false
            });
        }
    };
    var wrapped_success = data => {
        if (!bool_response || (bool_response && data == true)) {
            console.log(messages["success"]);
            clear_main_area();
            toastr.clear();
            success_callback();
        } else if (bool_response && data == false) {
            message_once(messages["not_ready"], spin_state);
            return false; // keep spinning
        } else {
            spin_error(`Invalid response to ${spin_state.type} request`, messages["invalid_response"], true);
        }
        return true; // stop spinning
    };
    var timeout_error = (jqxhr, status, error) => {
        message_once(messages["waiting"], spin_state);
        if (spin_state.count == warn_at) {
            toastr.warning(messages["wait_warn"], "Warning", {
                closeButton: true,
                timeOut: 0,
                extendedTimeOut: 0,
                tapToDismiss: false
            });
        }
        return false; // keep spinning
    };
    spin(url, bool_response, wrapped_success, timeout_error, timeout_error, spin_state);
}

/**
 * Test availability of a URL, and call a callback when done.
 * http://stackoverflow.com/q/25390206/347368
 * @param {String} url: URL to test availability of. Must return a 200 (302->200 is OK).
 * @param {String} callback: function to call once successfully connected.
 *
 */
export function test_ie_availability(url, success_callback) {
    var messages = {
        success: "IE connection succeeded, returning",
        waiting: "Interactive environment container is running, attempting to connect to the IE. Please wait...",
        wait_warn:
            "It is taking an usually long time to connect to the interactive environment. Attempts will continue but you may want to report this condition to a Galaxy administrator if it does not succeed soon.",
        error:
            "An error was encountered while attempting to connect to the interactive environment, contact your administrator."
    };
    var spin_state = make_spin_state("IE availability");
    spin_until(url, false, messages, success_callback, spin_state);
}

/**
 * Test a boolean (json) response from a URL, and call a callback when done.
 * http://stackoverflow.com/q/25390206/347368
 * @param {String} url: URL to test response of. Must return a 200 (302->200 is OK) and either `true` or `false`.
 * @param {String} callback: function to call once successfully connected.
 *
 */
export function load_when_ready(url, success_callback) {
    var messages = {
        success: "Galaxy reports IE container ready, returning",
        not_ready: "Galaxy is launching a container in which to run this interactive environment. Please wait...",
        unknown_response:
            "Galaxy failed to launch a container in which to run this interactive environment, contact a Galaxy administrator.",
        waiting: "Galaxy is launching a container in which to run this interactive environment. Please wait...",
        wait_warn:
            "It is taking an usually long time to start a container. Attempts will continue but you may want to report this condition to a Galaxy administrator if it does not succeed soon.",
        error:
            "Galaxy encountered an error while attempting to determine the readiness of this interactive environment's container, contact a Galaxy administrator."
    };
    var spin_state = make_spin_state("IE container readiness");
    spin_until(url, true, messages, success_callback, spin_state);
}
