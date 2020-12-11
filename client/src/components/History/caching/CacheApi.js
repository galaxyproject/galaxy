/**
 * Separated api from Worker definition so that we can use it without the worker
 * if desired.
 *
 * Note that database events are only consistent within the same database
 * instance, so a cache Event from outside the worker will not be heard by the
 * watchers inside the worker because those are actually 2 separate db
 * instances.
 */

import { pipe } from "rxjs";
import { content$, dscContent$ } from "./db/observables";
import { monitorQuery } from "./db/monitorQuery";

export * from "./db/promises";

export { loadDscContent } from "./loadDscContent";
export { loadHistoryContents, clearHistoryDateStore } from "./loadHistoryContents";
export { monitorHistoryContent } from "./monitorHistoryContent";
export { wipeDatabase } from "./db/pouch";

// generic content query monitor
export const monitorContentQuery = (cfg = {}) => {
    const monitorCfg = { db$: content$, ...cfg };
    return pipe(monitorQuery(monitorCfg));
};

// generic collection content monitor
export const monitorDscQuery = (cfg = {}) => {
    const monitorCfg = { db$: dscContent$, ...cfg };
    return pipe(monitorQuery(monitorCfg));
};
