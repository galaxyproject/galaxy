function append_notebook(){
    $('body').append(
        $('<object/>', {
            src: notebook_access_url,
            data: notebook_access_url,
            height: '100%',
            width: '100%',
        }).append(
            $('<embded/>', {
                src: notebook_access_url,
                data: notebook_access_url,
                height: '100%',
                width: '100%',
            })
        )
    );
}

function message_failed_auth(){
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
 * Load an interactive environment (IE) from a remote URL
 * @param {Boolean} password_auth Whether or not this resource requires password authentication
 * @param {String} password: password used to authenticate to the remote resource
 * @param {String} notebook_login_url: URL that should be POSTed to for login
 * @param {String} notebook_access_url: the URL embeded in the page and loaded
 * 
 * TODO: This function needs a lot of work to make it more generic:
 * TODO: exchange login_url, password, password_auth for a single function which encapsulates all the authentication procedure, as that will differ between IEs.
 */
function load_notebook(password_auth, password, notebook_login_url, notebook_access_url){
    if ( password_auth ) {
        // On document ready
        $( document ).ready(function() {
            // Make an AJAX POST
            $.ajax({
                type: "POST",
                // to the Login URL
                url: notebook_login_url,
                // With our password
                data: {
                    'password': notebook_pw
                },
                // If that is successful, load the notebook
                success: append_notebook,
                error: function(jqxhr, status, error){
                    message_failed_auth();
                    if(password_auth_jsvar && !apache_urls_jsvar){
                        // Failure happens due to CORS
                        append_notebook();
                    }else{
                        message_failed_connection();
                        // Do we want to try and load the notebook anyway? Just in case?
                    }
                }
            });
        });
    }
    else {
        // Not using password auth, just embed it to avoid content-origin issues.
        message_no_auth();
        $( document ).ready(function() {
            append_notebook();
        });
    }
}
