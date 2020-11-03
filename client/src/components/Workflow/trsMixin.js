import { getAppRoot } from "onload/loadConfig";
import TrsServerSelection from "./TrsServerSelection";
import TrsTool from "./TrsTool";
import { redirectOnImport } from "./utils";

export default {
    components: {
        TrsServerSelection,
        TrsTool,
    },
    methods: {
        importVersion(toolId, version, isRunFormRedirect = false) {
            this.services
                .importTrsTool(this.trsSelection.id, toolId, version.name)
                .then((response_data) => {
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    console.log("isRunFormRedirect", isRunFormRedirect);
                    redirectOnImport(getAppRoot(), response_data, isRunFormRedirect);
                })
                .catch((errorMessage) => {
                    this.errorMessage = errorMessage || "Import failed for an unknown reason.";
                });
        },
    },
};
