/**
 * Separated api from Worker definition so that we can use it without the worker
 * if desired.
 *
 * Note that database events are only consistent within the same database
 * instance, so a cache Event from outside the worker will not be heard by the
 * watchers inside the worker because those are actually 2 separate db
 * instances.
 */

import { content$, dscContent$ } from "./db/observables";
import { monitorQuery } from "./db/monitorQuery";

export * from "./db/promises";

export { loadDscContent } from "./loadDscContent";
export { loadHistoryContents, clearHistoryDateStore } from "./loadHistoryContents";
export { monitorHistoryContent, monitorCollectionContent } from "./monitorHistoryContent";
export { wipeDatabase } from "./db/wipeDatabase";

// generic content query monitor
export const monitorContentQuery = (cfg = {}) => {
    return monitorQuery({ db$: content$, ...cfg });
};

// generic collection content monitor
export const monitorDscQuery = (cfg = {}) => {
    return monitorQuery({ db$: dscContent$, ...cfg });
};
