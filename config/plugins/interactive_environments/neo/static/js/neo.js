// Load an interactive environment (IE) from a remote URL
// @param {String} notebook_access_url: the URL embeded in the page and loaded
function load_notebook(notebook_access_url){
    // When the page has completely loaded...
    $( document ).ready(function() {
        // Test if we can access the GIE, and if so, execute the function
        // to load the GIE for the user.
        test_ie_availability(notebook_access_url, function(){
            append_notebook(notebook_access_url);
        });
    });
}
