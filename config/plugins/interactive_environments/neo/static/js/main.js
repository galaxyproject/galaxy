// Globals to be rid of
var IES = window.IES;

// Load an interactive environment (IE) from a remote URL
// @param {String} notebook_access_url: the URL embeded in the page and loaded
function load_notebook(notebook_access_url) {
    // Test if we can access the GIE, and if so, execute the function
    // to load the GIE for the user.
    IES.test_ie_availability(notebook_access_url, function() {
        IES.append_notebook(notebook_access_url);
    });
}
