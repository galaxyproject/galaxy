function message_failed_connection(){
    toastr.error(
        "Could not connect to RStudio. Please contact your administrator.",
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
                xhrFields: {
                        withCredentials: true
                },
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

                    // Now we can login
                    $.ajax({
                        type: "POST",
                        // to the Login URL
                        url: notebook_login_url,
                        // With our password
                        data: {
                            'v': encrypted,
                            'persist': 1,
                            'clientPath': '/rstudio/auth-sign-in',
                            'appUri': '',
                        },
                        contentType: "application/x-www-form-urlencoded",
                        xhrFields: {
                            withCredentials: true
                        },
                        // If that is successful, load the notebook
                        success: function(){
                            append_notebook(notebook_access_url);
                        },
                        error: function(jqxhr, status, error){
                            message_failed_connection();
                            // Do we want to try and load the notebook anyway? Just in case?
                            append_notebook(notebook_access_url);
                        }
                    });
                }
            });

        });
    });
}
