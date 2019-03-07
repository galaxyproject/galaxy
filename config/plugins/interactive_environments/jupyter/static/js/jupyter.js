//Globals to be rid of
var IES = window.IES;
var toastr = window.toastr;

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
    // Test notebook_login_url for accessibility, executing the login+load function whenever
    // we've successfully connected to the IE.
    IES.test_ie_availability(notebook_login_url, function(){
        _handle_notebook_loading(password, notebook_login_url, notebook_access_url);
        keep_alive();
    });
}


function keep_alive(){
    /**
    * This is needed to keep the container alive. If the user leaves this site
    * this function is not constantly pinging the container, the container will
    * terminate itself.
    */
    var warn_at = 4;
    var count_max = 60;
    // we sleep 15 seconds between requests and the default timeout for the Jupyter container is 120 seconds, so start
    // with a pretty high ajax timeout. sleep starts low because we want to get the warning up pretty quickly
    var spin_state = IES.make_spin_state("IE keepalive", 8000, 16000, 2000, 5000, 15000, 5000, false);
    var success = function(){
        console.log("IE keepalive request succeeded");
        toastr.clear();
        if(spin_state.count >= warn_at){
            toastr.clear();
            toastr.success(
                "Interactive environment connection restored",
                {'closeButton': true, 'timeOut': 5000, 'extendedTimeOut': 2000, 'tapToDismiss': true}
            );
        }
        spin_state.count = 0;
        spin_state.timeout_count = 0;
        spin_state.error_count = 0;
        return false;  // keep spinning
    };
    var timeout_error = function(jqxhr, status, error){
        console.log("IE keepalive request failed " + spin_state.count + " time(s) of " + count_max + " max: " + status + ": " + error);
        if(spin_state.count == warn_at){
            toastr.warning(
                "Your browser has been unable to contact the interactive environment for "
                + spin_state.count + " consecutive attempts, if you do not reestablish "
                + "a connection, your IE container may be terminated.",
                "Warning",
                {'closeButton': true, 'timeOut': 0, 'extendedTimeOut': 0, 'tapToDismiss': false}
            );
            return false;  // keep spinning
        }else if(spin_state.count >= count_max){
            IES.spin_error("IE keepalive failure limit reached", "Lost connection to interactive environment, contact your administrator", false);
            return true;  // stop spinning
        }
    };
    console.log("IE keepalive worker starting");
    IES.spin(notebook_keepalive_url, false, success, timeout_error, timeout_error, spin_state);
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
                IES.append_notebook(notebook_access_url);
            },
            error: function(jqxhr, status, error){
                if(ie_password_auth){
                    // Failure happens due to CORS
                    message_failed_auth(password);
                    IES.append_notebook(notebook_access_url);
                }else{
                    message_failed_connection();
                    // Do we want to try and load the notebook anyway? Just in case?
                    IES.append_notebook(notebook_access_url);
                }
            }
        });
    }
    else {
        // Not using password auth, just embed it to avoid content-origin issues.
        message_no_auth();
        IES.append_notebook(notebook_access_url);
    }
}
