// Provides support for interacting with the GenomeSpace File Browser popup dialogue
import { getGalaxyInstance } from "app";

// tool form templates
export default {
    openFileBrowser: function(options) {
        let Galaxy = getGalaxyInstance();
        var GS_UI_URL = Galaxy.config.genomespace_ui_url;
        var GS_UPLOAD_URL = `${GS_UI_URL}upload/loadUrlToGenomespace.html?getLocation=true`;

        var newWin = window.open(GS_UPLOAD_URL, "GenomeSpace File Browser", "height=360px,width=600px");

        window.addEventListener(
            "message",
            e => {
                if (options.successCallback && e.data.destination) {
                    options.successCallback(e.data);
                }
            },
            false
        );

        newWin.focus();

        if (options["errorCallback"] != null) newWin.setCallbackOnGSUploadError = Galaxy.config["errorCallback"];
    }
};
