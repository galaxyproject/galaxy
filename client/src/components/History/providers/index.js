/**
 * Providers are renderless components that take raw inputs and monitor the
 * cache or other observables to emit end results as slot props.
 */

// These are pretty complex. Input parameters from "the top" are the History or
// selected collection, but they also expose slot-prop methods to update
// internal data such as user-provided filter parameters or the physical
// position of the scroll cursor in the list UI
export { default as HistoryContentProvider } from "./HistoryContentProvider";
export { default as CollectionContentProvider } from "./CollectionContentProvider";

// The DscProvider is only complex because we store dataset collection data in
// two places depending on its place in the data hierarchy. At the root level, a
// dataset collection is stored as history content. But a collection can nest
// other collections, and sub-collections are stored as collection-content
export { default as DscProvider } from "./DscProvider";

// Management for current user's histories. Largely a passthrough of store methods
export { default as UserHistories } from "./UserHistories";
