// Provides support for interacting with the GenomeSpace File Browser popup dialogue

// tool form templates
export default {
    openFileBrowser: function(options) {
        var GS_UI_URL = window.Galaxy.config.genomespace_ui_url;
        var GS_UPLOAD_URL = `${GS_UI_URL}jsCDK/loadUrlToGenomespace.html?getLocation=true` +
                            `&action=${encodeURIComponent(options.action)}` +
                            `&allowMultiple=${encodeURIComponent(options.multiple)}` +
                            `&selectType=${encodeURIComponent(options.select_type)}`;

        var newWin = window.open(GS_UPLOAD_URL, "GenomeSpace File Browser", "height=360px,width=600px");

        window.addEventListener(
            "message",
            e => {
                if (options.successCallback && (e.data.destinations || e.data.destination)) {
                    options.successCallback(e.data);
                }
            },
            false
        );

        newWin.focus();
    }
};
