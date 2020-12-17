// Exposes worker functions as promises or Observable operators
import { toPromise, toOperator } from "./workerClient";

/**
 * monitor cache for changes
 */
export const monitorContentQuery = toOperator("monitorContentQuery");
export const monitorDscQuery = toOperator("monitorDscQuery");
export const monitorHistoryContent = toOperator("monitorHistoryContent");

/**
 * Loaders
 */
export const loadHistoryContents = toOperator("loadHistoryContents");
export const loadDscContent = toOperator("loadDscContent");

/**
 * Cache promise functions
 */
export const cacheContent = toPromise("cacheContent");
export const getCachedContent = toPromise("getCachedContent");
export const uncacheContent = toPromise("uncacheContent");
export const bulkCacheContent = toPromise("bulkCacheContent");
export const cacheCollectionContent = toPromise("cacheCollectionContent");
export const getCachedCollectionContent = toPromise("getCachedCollectionContent");
export const bulkCacheDscContent = toPromise("bulkCacheDscContent");

// Debugging
export const wipeDatabase = toPromise("wipeDatabase");
export const clearHistoryDateStore = toPromise("clearHistoryDateStore");
