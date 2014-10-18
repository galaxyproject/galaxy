/**
 * Internal function to remove content from the main area and add the notebook.
 * Not idempotent
 */
function append_notebook(url){
    clear_main_area();
    $('#main').append('<object data="' + url + '" height="95%" width="100%">'
    +'<embed src="' + url + '" height="100%" width="100%"/></object>'
    );
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

