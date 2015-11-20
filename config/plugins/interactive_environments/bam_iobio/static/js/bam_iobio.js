function message_failed_auth(password){
    toastr.info(
        "Automatic authorization failed.",
        "Please login manually",
        {'closeButton': true, 'timeOut': 100000, 'tapToDismiss': false}
    );
}

function message_failed_connection(){
    toastr.error(
        "Could not connect to BAM iobio. Please contact your administrator.",
    "Security warning",
        {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': true}
    );
}

/**
 * Load an interactive environment (IE) from a remote URL
 * @param {String} password: password used to authenticate to the remote resource
 * @param {String} notebook_login_url: URL that should be POSTed to for login
 * @param {String} notebook_access_url: the URL embeded in the page and loaded
 *
 */
function load_notebook(notebook_access_url){
    $( document ).ready(function() {
        // Test notebook_login_url for accessibility, executing the login+load function whenever
        // we've successfully connected to the IE.
        test_ie_availability(notebook_access_url, function(){
            _handle_notebook_loading(notebook_access_url);
        });
    });
}

/**
 * Must be implemented by IEs
 */
function _handle_notebook_loading(notebook_access_url){
    append_notebook(notebook_access_url);
}
