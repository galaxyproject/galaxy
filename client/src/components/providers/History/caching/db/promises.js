/**
 * Same functionality as exposed in observables, but in promise form for one-off
 * utilities. A little easier to use if all you need to do is one thing.
 * However, for more complicated processing, I do recommend making the attempt
 * work in streams as you will have a lot more control over the throughput.
 */

import { of } from "rxjs";
import { firstValueFrom } from "utils/observable/firstValueFrom";

import {
    content$,
    cacheContent as cacheContentOp,
    getCachedContent as getCachedContentOp,
    uncacheContent as uncacheContentOp,
    bulkCacheContent as bulkCacheContentOp,
    bulkCacheDscContent as bulkCacheDscContentOp,
    getCachedCollectionContent as getCachedCollectionContentOp,
    cacheCollectionContent as cacheCollectionContentOp,
} from "./observables";

import { find } from "./find";

// result is an object pouch returns with the ID a rev, and whether it was
// actually updated or not (won't be if identical)
export const cacheContent = (rawProps, returnDoc) => firstValueFrom(of(rawProps).pipe(cacheContentOp(returnDoc)));
export const getCachedContent = (docId) => firstValueFrom(of(docId).pipe(getCachedContentOp()));
export const uncacheContent = (doc) => firstValueFrom(of(doc).pipe(uncacheContentOp()));
export const bulkCacheContent = (list, returnDocs) => firstValueFrom(of(list).pipe(bulkCacheContentOp(returnDocs)));

// collection content, collections are supposedly immutable after creation so
// all we really have is a bulk-load
export const cacheCollectionContent = (rawProps, returnDoc) =>
    firstValueFrom(of(rawProps).pipe(cacheCollectionContentOp(returnDoc)));
export const getCachedCollectionContent = (docId) => firstValueFrom(of(docId).pipe(getCachedCollectionContentOp()));
export const bulkCacheDscContent = (list, returnDocs) =>
    firstValueFrom(of(list).pipe(bulkCacheDscContentOp(returnDocs)));

// examples of how to fine-tune these to get specialized functionality
export const getContentByTypeId = async (history_id, type_id) => {
    const selector = { history_id, type_id };
    const index = { fields: ["history_id", "type_id"] };
    const request = { selector, index, limit: 1 };
    const obs$ = of(request).pipe(find(content$));
    const results = await firstValueFrom(obs$);
    return results.length > 0 ? results[0] : null;
};
