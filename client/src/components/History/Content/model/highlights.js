/**
 * Specifies highlighted items in the history listing. The `highlight` property is passed to
 * the content item component and can be used to modify its appearance.
 * TO DO: Consider case where parameter history is different and hence inputs cannot be seen
 *        in the current panel.
 */
import axios from "axios";
import { prependPath } from "utils/redirect";
import { deepeach } from "utils/utils";
import { LastQueue } from "utils/promise-queue";

// add promise queue
const lastQueue = new LastQueue(300);

/** Local cache for parameter requests */
const paramStash = new Map();

/** Performs request to obtain dataset parameters */
async function getDatasetParameters(datasetId, jobId) {
    if (!paramStash.has(datasetId)) {
        const url = jobId
            ? `api/jobs/${jobId}/parameters_display`
            : `api/datasets/${datasetId}/parameters_display?hda_ldda=hda`;
        const { data } = await lastQueue.enqueue(axios.get, prependPath(url));
        paramStash.set(datasetId, data);
    }
    return paramStash.get(datasetId);
}

/** Returns item key */
function getKey(details) {
    if (details.id && details.src) {
        const historyContentType = details.src == "hda" ? "dataset" : "dataset_collection";
        return `${details.id}-${historyContentType}`;
    }
    return null;
}

/** Returns highlighting details */
export async function getHighlights(item, itemKey) {
    const highlights = {};
    const { outputs, parameters } = await getDatasetParameters(item.id, item.job_source_id);
    deepeach(parameters, (details) => {
        const key = getKey(details);
        if (key) {
            highlights[key] = "input";
        }
    });
    deepeach(outputs, (details) => {
        const key = getKey(details);
        if (key) {
            // some other item created this item (e.g.: inheritance)
            if (key != itemKey) {
                highlights[itemKey] = "output";
                highlights[key] = "input";
            } else {
                highlights[key] = "output";
            }
        }
    });
    // highlights only has item itself as an output (i.e.: no inputs)
    if (highlights[itemKey] === "output" && Object.keys(highlights).length == 1) {
        highlights[itemKey] = "noInputs";
    }
    // TO DO: Consider case where a job created multiple items (all highlights are outputs)
    return highlights;
}
