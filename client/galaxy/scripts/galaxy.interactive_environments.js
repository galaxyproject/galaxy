/**
 * Internal function to remove content from the main area and add the notebook.
 * Not idempotent
 */
function append_notebook(url){
    clear_main_area();
    $('#main').append('<iframe frameBorder="0" seamless="seamless" style="width: 100%; height: 100%; overflow:hidden;" scrolling="no" src="'+ url +'"></iframe>'
    );
}

function clear_main_area(){
    $('#spinner').remove();
    $('#main').children().remove();
}

function display_spinner(){
        $('#main').append('<img id="spinner" src="' + galaxy_root + 'static/style/largespinner.gif" style="position:absolute;margin:auto;top:0;left:0;right:0;bottom:0;">');
}

function not_ready(timeout, timeout_values, timeout_time_max, timeout_time_step, message, type) {
    if(timeout_values.count == 0){
        display_spinner();
        toastr.info(
            message,
            {'closeButton': true, 'tapToDismiss': false}
        );
    }
    timeout_values.count++;
    if(timeout_values.time < timeout_time_max){
        timeout_values.time += timeout_time_step;
    }
    console.log(type + " request " + timeout_values.count + " sleeping " + timeout_values.time / 1000 + "s");
    window.setTimeout(timeout, timeout_values.time)
}

/**
 * Check a URL for a boolean true/false and call a callback when done.
 */
function make_spin_state(type, ajax_timeout_init, ajax_timeout_max, ajax_timeout_step, sleep_init, sleep_max, sleep_step){
    var s = {};
    s.type = (typeof type !== 'undefined') ? type : "GIE spin";
    s.ajax_timeout = (typeof ajax_timeout_init !== 'undefined') ? ajax_timeout_init : 500;
    s.ajax_timeout_max = (typeof ajax_timeout_max !== 'undefined') ? ajax_timeout_max : 8000;
    s.ajax_timeout_step = (typeof ajax_timeout_step !== 'undefined') ? ajax_timeout_step : 250;
    s.sleep = (typeof sleep_init !== 'undefined') ? sleep_init : 1000;
    s.sleep_max = (typeof slee_max !== 'undefined') ? slee_max : 10000;
    s.sleep_step = (typeof sleep_step !== 'undefined') ? sleep_step : 500;
    s.count = 0;
    reutrn s;
}

function make_error_callback(console_msg, user_msg, clear){
    var f = function() {
        log.console(console_msg);
        if(clear) clear_main_area();
        if(typeof user_msg == "string"){
            toastr.clear();
            toastr.error(
                error_message,
                "Error",
                {'closeButton': true, 'tapToDismiss': false}
            );
        }
    return f;
}

function spin_again(spin_state){
    spin_state.count++;
    if(spin_state.sleep < spin_state.sleep_max){
        spin_state.sleep += spin_state.step;
    }
    console.log(spin_state.type + " request " + spin_state.count + " sleeping " + spin_state.sleep / 1000 + "s");
    window.setTimeout(spin_state.spinner, spin_state.sleep)

function spin(url, bool_response, success_callback, timeout_callback, error_callback, spin_state){
    var spinner = function(){
        var ajax_params = {
            url: url,
            xhrFields: {
                withCredentials: true
            },
            type: "GET",
            timeout: spin_state.ajax_timeout,
            success: success_callback,
            error: function(jqxhr, status, error){
                if(status == "timeout"){
                    if(spin_state.ajax_timeout < spin_state.ajax_timeout_max){
                        spin_state.ajax_timeout += spin_state.ajax_timeout_step;
                    }
                    spin_state.count++;
                    timeout_callback();
                    spin_again(spin_state);
                }else{
                    error_callback();
                }
            },
        }
        if(bool_response) ajax_params["dataType"] = "json";
        $.ajax(ajax_params);
    }
    spin_state.spinner = spinner;
    window.setTimeout(spinner, spin_state.sleep);
}

function spin_until(url, bool_response, messages, success_callback, spin_state){
    var message_once = function(message, spin_state) {
        if(spin_state.count == 0){
            display_spinner();
            toastr.info(
                messages["not_ready"],
                {'closeButton': true, 'tapToDismiss': false}
            );
        }
    }
    var wrapped_success = function(data){
        if(!bool_response || (bool_response && data == true)){
            console.log(messages["success"]);
            clear_main_area();
            toastr.clear();
            success_callback();
        }else if(bool_response && data == false){
            message_once(messages["not_ready"], spin_state);
            spin_again(spin_state);
        }else{
            make_error_callback("Invalid response to spin request", messages["invalid_response"], true)();
        }
    }
    spin(
        url,
        bool_response,
        wrapped_success,
        function(){
            message_once(messages["timeout"], spin_state);
            spin_again(spin_state);
        },
        make_error_callback("Error in spin request", messages["error"], true),
        spin_state
    );
}


function load_when_ready(url, success_callback){
    var messages = {
        success: "Galaxy reports IE container ready, returning",
        not_ready: "Galaxy is launching a container in which to run this interactive environment. Please wait...",
        unknown_response: "Galaxy failed to launch a container in which to run this interactive environment, contact your administrator.",
        timeout: "Galaxy is launching a container in which to run this interactive environment. Please wait...",
        error: "Galaxy encountered an error while attempting to determine the readiness of this interactive environment's container, contact your administrator."
    }
    var spin_state = make_spin_state("IE container readiness");
    spin_until(url, true, messages, success_callback);
}


function test_ie_availability(url, success_callback){
    var messages = {
        success: "IE connection succeeded, returning",
        timeout: "Attempting to connect to the interactive environment. Please wait...",
        error: "An error was encountered while attempting to connect to the interactive environment, contact your administrator."
    }
    var spin_state = make_spin_state("IE availability");
    spin(url, false, messages, success_callback);
}


/**
 * Test availability of a URL, and call a callback when done.
 * http://stackoverflow.com/q/25390206/347368
 * @param {String} url: URL to test availability of. Must return a 200 (302->200 is OK).
 * @param {String} callback: function to call once successfully connected.
 *
 */
function old_test_ie_availability(url, success_callback){
    var ajax_timeout = 500;
    var ajax_timeout_max = 10000;
    var ajax_timeout_step = 250;
    var request_count = 0;
    /* in leiu of a container status endpoint */
    var request_count_max = 90;
    display_spinner();
    interval = setInterval(function(){
        $.ajax({
            url: url,
            xhrFields: {
                withCredentials: true
            },
            type: "GET",
            timeout: ajax_timeout,
            success: function(){
                console.log("IE is available (connection succeeded), returning");
                clearInterval(interval);
                success_callback();
            },
            error: function(jqxhr, status, error){
                if(status == "timeout"){
                    if(ajax_timeout < ajax_timeout_max){
                        ajax_timeout += ajax_timeout_step;
                    }
                }else{
                    request_count++;
                    console.log("Availability request " + request_count);
                    if(request_count > 30){
                        clearInterval(interval);
                        clear_main_area();
                        toastr.error(
                            "Could not connect to IE, contact your administrator",
                            "Error",
                            {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': false}
                        );
                    }
                }
            }
        });
    }, 1000);
}
