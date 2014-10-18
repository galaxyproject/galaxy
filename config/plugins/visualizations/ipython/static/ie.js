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

