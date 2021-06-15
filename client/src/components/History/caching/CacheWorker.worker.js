/**
 * Instantiates worker with with externally defined api
 */

// TODO: isn't @babel/polyfill bad now?
import "@babel/polyfill";
import { expose } from "threads/worker";
import { asObservable } from "./asObservable";
import { configure } from "./workerConfig";
import * as api from "./CacheApi";

const {
    monitorContentQuery,
    monitorDscQuery,
    monitorHistoryContent,
    monitorCollectionContent,
    loadHistoryContents,
    loadDscContent,
    pollHistory,
    ...promises
} = api;

expose({
    configure,

    // observable operators
    monitorContentQuery: asObservable(monitorContentQuery),
    monitorDscQuery: asObservable(monitorDscQuery),
    monitorHistoryContent: asObservable(monitorHistoryContent),
    monitorCollectionContent: asObservable(monitorCollectionContent),
    loadHistoryContents: asObservable(loadHistoryContents),
    loadDscContent: asObservable(loadDscContent),
    pollHistory: asObservable(pollHistory),

    // promise functions
    ...promises,
});
