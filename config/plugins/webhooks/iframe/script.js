(function () {
    var galaxyRoot = typeof Galaxy !== "undefined" ? Galaxy.root : "/";
    var container = document.getElementById("iframe");
    if (!container) return;

    fetch(galaxyRoot + "api/webhooks/iframe/data")
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            if (!data || !data.src) return;
            var title = data.title || "";
            var height = data.height || 1000;
            var header = title
                ? '<div id="iframe-header"><div id="iframe-name">' + title + "</div></div>"
                : "";
            container.innerHTML =
                header +
                '<iframe id="webhook-iframe" src="' +
                data.src +
                '" style="width:100%; height:' +
                height +
                'px; border:none;"></iframe>';
        })
        .catch(function (e) {
            console.error("Galaxy iframe webhook error:", e);
        });
})();
