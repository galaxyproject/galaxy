var IES = window.IES;

function load_askomics(url){
    $( document ).ready(function() {
        IES.test_ie_availability(url, function(){
            IES.append_notebook(url);
        });
    });
}
