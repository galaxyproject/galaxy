/**
 * A component mixin and a set of observable utilities used in common by HicstoryContentProvider and
 * CollectionContentProvider
 */

// base component definition for History & Collection content providers
export { ContentProvider, defaultPayload } from "./ContentProvider";

// aggreagtion functions collect an initial query and merge in subsequent updates which appear int
// he cache over time to present a unified list of results ordered by a relevant key
export { buildContentResult, newUpdateMap, processContentUpdate, getKeyForUpdateMap } from "./aggregation";
export { aggregateCacheUpdates } from "./aggregateCacheUpdates";

// configurable operators encapsulating shared behavior for content and collections
export { processContentStreams } from "./processContentStreams";

// utils
export { paginationEqual } from "./helpers";
