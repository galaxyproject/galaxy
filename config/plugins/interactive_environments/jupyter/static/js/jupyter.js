function message_failed_auth(password){
    toastr.info(
        "Automatic authorization failed. You can manually login with:<br>" + password + "<br> <a href='https://github.com/bgruening/galaxy-ipython/wiki/Automatic-Authorization-Failed' target='_blank'>More details ...</a>",
        "Please login manually",
        {'closeButton': true, 'timeOut': 100000, 'tapToDismiss': false}
    );
}

function message_failed_connection(){
    toastr.error(
        "Could not connect to Jupyter Notebook. Please contact your administrator. <a href='https://github.com/bgruening/galaxy-ipython/wiki/Could-not-connect-to-IPython-Notebook' target='_blank'>More details ...</a>",
    "Security warning",
        {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': true}
    );
}

function message_no_auth(){
    // No longer a security issue, proxy validates Galaxy session token.
    /*
    toastr.warning(
        "IPython Notebook was lunched without authentication. This is a security issue. <a href='https://github.com/bgruening/galaxy-ipython/wiki/IPython-Notebook-was-lunched-without-authentication' target='_blank'>More details ...</a>",
        "Security warning",
        {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': false}
    );
    */
}


/**
 * Load an interactive environment (IE) from a remote URL
 * @param {String} password: password used to authenticate to the remote resource
 * @param {String} notebook_login_url: URL that should be POSTed to for login
 * @param {String} notebook_access_url: the URL embeded in the page and loaded
 *
 */
function load_notebook(password, notebook_login_url, notebook_access_url){
    $( document ).ready(function() {
        // Test notebook_login_url for accessibility, executing the login+load function whenever
        // we've successfully connected to the IE.
        test_ie_availability(notebook_login_url, function(){
            _handle_notebook_loading(password, notebook_login_url, notebook_access_url);
        });
    });
}


function keep_alive(){
    /**
    * This is needed to keep the container alive. If the user leaves this site
    * this function is not constantly pinging the container, the container will
    * terminate itself.
    */

    var request_count = 0;
    interval = setInterval(function(){
        $.ajax({
            url: notebook_access_url,
            xhrFields: {
                withCredentials: true
            },
            type: "GET",
            timeout: 500,
            success: function(){
                console.log("Connected to IE, returning");
            },
            error: function(jqxhr, status, error){
                request_count++;
                console.log("Request " + request_count);
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
        });
    }, 30000);
}


/**
 * Must be implemented by IEs
 */
function _handle_notebook_loading(password, notebook_login_url, notebook_access_url){
    if ( ie_password_auth ) {
        // Make an AJAX POST
        $.ajax({
            type: "POST",
            // to the Login URL
            url: notebook_login_url,
            // With our password
            data: {
                'password': password
            },
            xhrFields: {
                withCredentials: true
            },
            // If that is successful, load the notebook
            success: function(){
                append_notebook(notebook_access_url);
            },
            error: function(jqxhr, status, error){
                if(ie_password_auth){
                    // Failure happens due to CORS
                    message_failed_auth(password);
                    append_notebook(notebook_access_url);
                }else{
                    message_failed_connection();
                    // Do we want to try and load the notebook anyway? Just in case?
                    append_notebook(notebook_access_url);
                }
            }
        });
    }
    else {
        // Not using password auth, just embed it to avoid content-origin issues.
        message_no_auth();
        append_notebook(notebook_access_url);
    }
}
