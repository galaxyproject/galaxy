define("mvc/tool/tool-genomespace", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    exports.default = {
        openFileBrowser: function openFileBrowser(options) {
            var GS_UI_URL = window.Galaxy.config.genomespace_ui_url;
            var GS_UPLOAD_URL = GS_UI_URL + "upload/loadUrlToGenomespace.html?getLocation=true";

            var newWin = window.open(GS_UPLOAD_URL, "GenomeSpace File Browser", "height=360px,width=600px");

            successCalBack = options["successCallback"];
            window.addEventListener("message", function(e) {
                successCalBack(e.data);
            }, false);

            newWin.focus();

            if (options["errorCallback"] != null) newWin.setCallbackOnGSUploadError = config["errorCallback"];
        }
    };
});
//# sourceMappingURL=../../../maps/mvc/tool/tool-genomespace.js.map
