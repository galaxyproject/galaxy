//Allow change tab on event=====================================================
function change_favicon(img) {
    var favicon = document.createElement("link");
    favicon.id = "tabicon";
    favicon.setAttribute("rel", "shortcut icon");
    var head = document.querySelector("head");
    head.appendChild(favicon);
    favicon.setAttribute("type", "image/png");
    favicon.setAttribute("href", img);
}

//Check if browser is hidden-aware==============================================
function hidden_permit() {
    var browsers = ["webkit", "moz", "ms", "o"];
    if ("hidden" in document) {
        return "hidden";
    }
    for (var i = 0; i < browsers.length; i++) {
        if (browsers[i] + "Hidden" in document) {
            return browsers[i] + "Hidden";
        }
    }
    return null;
}

//Find out if browser tab is hidden=============================================
function is_hidden() {
    var state = hidden_permit();
    if (!state) {
        return false;
    }
    return document[state];
}

//Generate new tab message to display on update in window=======================
function hidden_count(current) {
    if (is_hidden()) {
        if (current === 1) {
            document.title = "Galaxy (1 job completed)";
        } else {
            document.title = "Galaxy (" + current + " jobs completed)";
        }
    }
}

export default {
    change_favicon: change_favicon,
    hidden_permit: hidden_permit,
    is_hidden: is_hidden,
    hidden_count: hidden_count,
};
