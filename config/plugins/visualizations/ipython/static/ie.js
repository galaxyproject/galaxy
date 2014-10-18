/**
 * Internal function to remove content from the main area and add the notebook.
 * Not idempotent
 */
function append_notebook(url){
    clear_main_area();
    //$('#main').append('<object data="' + url + '" height="95%" width="100%">'
    //+'<embed src="' + url + '" height="100%" width="100%"/></object>'
    //);
}

function clear_main_area(){
    $('#spinner').remove();
    $('#main').children().remove();
}

function display_spinner(){
        $('#main').append('<img id="spinner" src="' + galaxy_root + '/static/style/largespinner.gif" style="position:absolute;margin:auto;top:0;left:0;right:0;bottom:0;">');
}


/**
 * Initial version of function to test availability of URL/resource
 * http://stackoverflow.com/q/25390206/347368
 */
function test_ie_availability(url, success_callback){
    var request_count = 0;
    display_spinner();
    interval = setInterval(function(){
        $.ajax({
            type: "GET",
            url: url + "?ie_test=1",
            success: function(){
                clearInterval(interval);
                success_callback();
            },
            error: function(){
                request_count++;
                if(request_count > 30){
                    clearInterval(interval);
                    clear_main_area();
                    console.log("Gave up after 15 seconds");
                }
            }
        });
    }, 500);
}

/**
 * Load an interactive environment (IE) from a remote URL
 * @param {String} password: password used to authenticate to the remote resource
 * @param {String} notebook_login_url: URL that should be POSTed to for login
 * @param {String} notebook_access_url: the URL embeded in the page and loaded
 *
 */
function load_notebook(password, notebook_login_url, notebook_access_url, callback_function){
    $( document ).ready(function() {
        test_ie_availability(notebook_access_url, function(){
            callback_function(notebook_login_url, notebook_access_url);
        });
    });
}
