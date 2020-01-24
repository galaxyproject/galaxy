//Globals to be rid of
var IES = window.IES;
var toastr = window.toastr;

function load_notebook(url) {
    IES.test_ie_availability(url, function() {
        IES.append_notebook(url);
    });
}
