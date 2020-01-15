// Globals to be rid of
var IES = window.IES;

// Load an interactive environment (IE) from a remote URL
// @param {String} url: the URL embeded in the page and loaded
function load_notebook(url){
    // Test if we can access the GIE, and if so, execute the function
    // to load the GIE for the user.
    $(document).ready(function() {
    	IES.test_ie_availability(url, function() {
	        IES.append_notebook(url);
	    });
	});
}
