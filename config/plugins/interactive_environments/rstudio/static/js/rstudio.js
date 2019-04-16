// Assumed globals we need to get rid of
var IES = window.IES;
var toastr = window.toastr;

function message_failed_connection(){
    toastr.error(
        "Could not connect to RStudio. Please contact your administrator.",
        "Security warning",
        {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': true}
    );
}


/**
 * Load an interactive environment (IE) from a remote URL
 * @param {String} notebook_access_url: the URL embeded in the page and loaded
 *
 */
function load_notebook(notebook_access_url){
    // Test notebook_login_url for accessibility, executing the login+load function whenever
    // we've successfully connected to the IE.
    IES.test_ie_availability(notebook_access_url, function(){
        $.ajax({
            type: 'GET',
            url: notebook_access_url,
            success: function(response_text){
                IES.append_notebook(notebook_access_url);
            }
        });

    });
}
