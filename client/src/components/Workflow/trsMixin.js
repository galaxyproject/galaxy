import { getAppRoot } from "onload/loadConfig";
import TrsServerSelection from "./TrsServerSelection";
import TrsTool from "./TrsTool";

export default {
    components: {
        TrsServerSelection,
        TrsTool,
    },
    methods: {
        importVersion(toolId, version) {
            this.services
                .importTrsTool(this.trsSelection.id, toolId, version.name)
                .then((response_data) => {
                    // copied from the WorkflowImport, de-duplicate somehow
                    window.location = `${getAppRoot()}workflows/list?message=${response_data.message}&status=success`;
                })
                .catch((errorMessage) => {
                    this.errorMessage = errorMessage || "Import failed for an unknown reason.";
                });
        },
    },
};
