//Globals to be rid of
var IES = window.IES;

// Load an interactive environment (IE) from a remote URL
// @param {String} hicexplorer_access_url: the URL embeded in the page and loaded
function load_hicexplorer(hicexplorer_access_url) {
    // When the page has completely loaded...
    $(document).ready(function() {
        // Test if we can access the GIE, and if so, execute the function
        // to load the GIE for the user.
        IES.test_ie_availability(hicexplorer_access_url, function() {
            IES.append_notebook(hicexplorer_access_url);
        });
    });
}
