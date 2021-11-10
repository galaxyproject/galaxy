// Exposes worker functions as promises or Observable operators

export { monitorContentQuery, monitorDscQuery, monitorHistoryContent, monitorCollectionContent } from "./CacheApi";

export { loadHistoryContents, loadDscContent } from "./CacheApi";

export {
    cacheContent,
    getCachedContent,
    uncacheContent,
    bulkCacheContent,
    cacheCollectionContent,
    getCachedCollectionContent,
    bulkCacheDscContent,
    getContentByTypeId,
} from "./CacheApi";

export { wipeDatabase, clearHistoryDateStore } from "./CacheApi";

// TODO: The above exports bypass the worker completely for now, swap back to below to use.
//import { toPromise, toOperator } from "./workerClient";
///**
// * monitor cache for changes
// */
//export const monitorContentQuery = toOperator("monitorContentQuery");
//export const monitorDscQuery = toOperator("monitorDscQuery");
//export const monitorHistoryContent = toOperator("monitorHistoryContent");
//export const monitorCollectionContent = toOperator("monitorCollectionContent");
//
///**
// * Loaders
// */
//export const loadHistoryContents = toOperator("loadHistoryContents");
//export const loadDscContent = toOperator("loadDscContent");
//
///**
// * Cache promise functions
// */
//export const cacheContent = toPromise("cacheContent");
//export const getCachedContent = toPromise("getCachedContent");
//export const uncacheContent = toPromise("uncacheContent");
//export const bulkCacheContent = toPromise("bulkCacheContent");
//export const cacheCollectionContent = toPromise("cacheCollectionContent");
//export const getCachedCollectionContent = toPromise("getCachedCollectionContent");
//export const bulkCacheDscContent = toPromise("bulkCacheDscContent");
//export const getContentByTypeId = toPromise("getContentByTypeId");
//
//// Debugging
//export const wipeDatabase = toPromise("wipeDatabase");
//export const clearHistoryDateStore = toPromise("clearHistoryDateStore");
