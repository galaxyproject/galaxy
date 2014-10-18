/**
 * Internal function to remove content from the main area and add the notebook.
 * Not idempotent
 */
function append_notebook(url){
    $('#spinner').remove();
    $('#main').append('<object data="' + url + '" height="95%" width="100%">'
    +'<embed src="' + url + '" height="100%" width="100%"/></object>'
    );
}

function message_failed_auth(password){
    toastr.info(
        "Automatic authorization failed. You can manually login with:<br>" + password + "<br> <a href='https://github.com/bgruening/galaxy-ipython/wiki/Automatic-Authorization-Failed' target='_blank'>More details ...</a>",
        "Please login manually",
        {'closeButton': true, 'timeOut': 100000, 'tapToDismiss': false}
    );
}

function message_failed_connection(){
    toastr.error(
        "Could not connect to IPython Notebook. Please contact your administrator. <a href='https://github.com/bgruening/galaxy-ipython/wiki/Could-not-connect-to-IPython-Notebook' target='_blank'>More details ...</a>",
    "Security warning",
        {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': true}
    );
}

function message_no_auth(){
    toastr.warning(
        "IPython Notebook was lunched without authentication. This is a security issue. <a href='https://github.com/bgruening/galaxy-ipython/wiki/IPython-Notebook-was-lunched-without-authentication' target='_blank'>More details ...</a>",
        "Security warning",
        {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': false}
    );
}

/**
 * Initial version of function to test availability of URL/resource
 * http://stackoverflow.com/q/25390206/347368
 */
function test_ie_availability(url){
    interval = setInterval(function(){
        $.ajax({
            type: "GET",
            url: url,
            success: function(){
                clearInterval(interval);
                return true;
                //_handle_notebook_loading(password_auth, password, notebook_login_url, notebook_access_url, apache_urls, docker_delay);
            }
        });
    }, 500);
}

/**
 * Load an interactive environment (IE) from a remote URL
 * @param {Boolean} password_auth Whether or not this resource requires password authentication
 * @param {String} password: password used to authenticate to the remote resource
 * @param {String} notebook_login_url: URL that should be POSTed to for login
 * @param {String} notebook_access_url: the URL embeded in the page and loaded
 * @param {Boolean} apache_urls: Proxying is done outside of galaxy in the webserver
 * @param {String} galaxy_root: root of the galaxy server, used for finding the static spinner.gif that ships with galaxy.
 * 
 * TODO: This function needs a lot of work to make it more generic:
 * TODO: exchange login_url, password, password_auth for a single function which encapsulates all the authentication procedure, as that will differ between IEs.
 */
function load_notebook(password_auth, password, notebook_login_url, notebook_access_url, apache_urls, galaxy_root){
    $( document ).ready(function() {
        $('#main').append('<img id="spinner" src="' + galaxy_root + '/static/style/largespinner.gif" style="position:absolute;margin:auto;top:0;left:0;right:0;bottom:0;">');
        interval = setInterval(function(){
            $.ajax({
                type: "GET",
                url: notebook_access_url,
                success: function(){
                    clearInterval(interval);
                    _handle_notebook_loading(password_auth, password, notebook_login_url, notebook_access_url, apache_urls);
                },
                error: function(){
                    console.log("Some error");
                }
            });
        }, 500);
    });
}

/**
 * Internal function
 */
function _handle_notebook_loading(password_auth, password, notebook_login_url, notebook_access_url, apache_urls){
    if ( password_auth ) {
        // Make an AJAX POST
        $.ajax({
            type: "POST",
            // to the Login URL
            url: notebook_login_url,
            // With our password
            data: {
                'password': password
            },
            // If that is successful, load the notebook
            success: function(){
                append_notebook(notebook_access_url);
            },
            error: function(jqxhr, status, error){
                if(password_auth && !apache_urls){
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
