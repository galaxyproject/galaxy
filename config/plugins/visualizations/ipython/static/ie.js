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

