function load_notebook(url){
    $( document ).ready(function() {
        test_ie_availability(url, function(){
            append_notebook(url)
        });
    });
}

function append_notebook(url){
    clear_main_area();
    $('#main').append('<iframe frameBorder="0" seamless="seamless" style="width: 100%; height: 100%; overflow:auto;" scrolling="yes" src="'+ url +'"></iframe>'
    );
}


function keep_alive(notebook_access_url){
    /**
    * This is needed to keep the container alive. If the user leaves this site
    * this function is not constantly pinging the container, the container will
    * terminate itself.
    */

    var request_count = 0;
    interval = setInterval(function(){
        $.ajax({
            url: notebook_access_url,
            xhrFields: {
                withCredentials: true
            },
            type: "GET",
            timeout: 500,
            success: function(){
                console.log("Connected to IE, returning");
            },
            error: function(jqxhr, status, error){
                request_count++;
                console.log("Request " + request_count);
                if(request_count > 30){
                    clearInterval(interval);
                    clear_main_area();
                    toastr.error(
                        "Could not connect to IE, contact your administrator",
                        "Error",
                        {'closeButton': true, 'timeOut': 20000, 'tapToDismiss': false}
                    );
                }
            }
        });
    }, 10000);
}

