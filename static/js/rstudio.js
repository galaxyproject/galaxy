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


/**
 * Load an interactive environment (IE) from a remote URL
 * @param {String} password: password used to authenticate to the remote resource
 * @param {String} notebook_login_url: URL that should be POSTed to for login
 * @param {String} notebook_access_url: the URL embeded in the page and loaded
 *
 */
function load_notebook(notebook_login_url, notebook_access_url, notebook_pubkey_url, username){
    $( document ).ready(function() {
        // Test notebook_login_url for accessibility, executing the login+load function whenever
        // we've successfully connected to the IE.
        test_ie_availability(notebook_pubkey_url, function(){
            var payload = username + "\n" + ie_password;
            $.ajax({
                type: 'GET',
                url: notebook_pubkey_url,
                success: function(response_text){
                    var chunks = response_text.split(':', 2);
                    var exp = chunks[0];
                    var mod = chunks[1];
                    console.log("Found " + exp +" and " + mod);
                    var rsa = new RSAKey();
                    rsa.setPublic(mod, exp);
                    console.log("Encrypting '" + username + "', '" + ie_password + "'");
                    var enc_hex = rsa.encrypt(payload);
                    var encrypted = hex2b64(enc_hex);
                    console.log("E: " + encrypted);
                    _handle_notebook_loading(encrypted, notebook_login_url, notebook_access_url);
                }
            });

        });
    });
}

/**
 * Must be implemented by IEs
 */
function _handle_notebook_loading(password, notebook_login_url, notebook_access_url){
    if ( ie_password_auth ) {
        $('form[name=realform]').attr('action', notebook_login_url);
        $('input[name=v]').val(password);
        $('form[name=realform]').submit();
    }
    else {
        // Not using password auth, just embed it to avoid content-origin issues.
        message_no_auth();
        append_notebook(notebook_access_url);
    }
}
