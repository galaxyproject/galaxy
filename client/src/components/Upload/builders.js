/*
 * Interface with rule builder
 */
import { getGalaxyInstance } from "app";

/** Populates collection builder with uploaded files */
export function collectionBuilder(historyId, type, uploadValues) {
    const Galaxy = getGalaxyInstance();
    const models = {};
    uploadValues.forEach((model) => {
        const outputs = model.outputs;
        if (outputs) {
            Object.entries(outputs).forEach((output) => {
                const outputDetails = output[1];
                models[outputDetails.id] = outputDetails;
            });
        } else {
            console.debug("Warning, upload response does not contain outputs.", model);
        }
    });
    // Build selection object
    const selection = {
        models: Object.values(models),
        historyId: historyId,
    };
    Galaxy.currHistoryPanel.buildCollection(type, selection);
}
