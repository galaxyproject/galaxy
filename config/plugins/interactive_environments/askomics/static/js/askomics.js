function append_notebook(url){
    clear_main_area();
    $('#main').append('<iframe frameBorder="0" seamless="seamless" style="width: 100%; height: 100%; overflow:auto;" scrolling="yes" src="'+ url +'"></iframe>'
    );
}


function load_askomics(url){
    $( document ).ready(function() {
        test_ie_availability(url, function(){
            append_notebook(url)
        });
    });
}
