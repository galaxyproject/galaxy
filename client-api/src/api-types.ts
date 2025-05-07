/**
 * This file re-exports the types we want to use from the Galaxy API.
 * It serves as a compatibility layer to avoid importing directly from the
 * symlinked files, which would require all of Galaxy's dependencies.
 */

// Import types from the symlinked files
import { type components, type GalaxyApiPaths } from "./api/schema";

// We only need the types, not the code that depends on Galaxy's implementation
export type { components, GalaxyApiPaths };

// Re-export specific types
export type HistorySummary = components["schemas"]["HistorySummary"];
export type HistoryDetailed = components["schemas"]["HistoryDetailed"];
export type HDASummary = components["schemas"]["HDASummary"];
export type HDADetailed = components["schemas"]["HDADetailed"];
export type DCESummary = components["schemas"]["DCESummary"];
export type HDCASummary = components["schemas"]["HDCASummary"];
export type HDCADetailed = components["schemas"]["HDCADetailed"];
export type DCObject = components["schemas"]["DCObject"];
export type HDAObject = components["schemas"]["HDAObject"];
export type HDAInaccessible = components["schemas"]["HDAInaccessible"];
export type DatasetTextContentDetails = components["schemas"]["DatasetTextContentDetails"];
export type DatasetStorageDetails = components["schemas"]["DatasetStorageDetails"];
export type DatasetCollectionAttributes = components["schemas"]["DatasetCollectionAttributesResult"];
export type ConcreteObjectStoreModel = components["schemas"]["ConcreteObjectStoreModel"];
export type MessageException = components["schemas"]["MessageExceptionModel"];
export type DatasetHash = components["schemas"]["DatasetHash"];
export type DatasetSource = components["schemas"]["DatasetSource"];
export type DatasetTransform = components["schemas"]["DatasetSourceTransform"];
export type StoreExportPayload = components["schemas"]["StoreExportPayload"];
export type ModelStoreFormat = components["schemas"]["ModelStoreFormat"];
export type ObjectExportTaskResponse = components["schemas"]["ObjectExportTaskResponse"];
export type ExportObjectRequestMetadata = components["schemas"]["ExportObjectRequestMetadata"];
export type ExportObjectResultMetadata = components["schemas"]["ExportObjectResultMetadata"];
export type AsyncTaskResultSummary = components["schemas"]["AsyncTaskResultSummary"];

// Define utility types that may be used in the client
export type HistorySortByLiteral = "create_time" | "name" | "update_time" | "username" | undefined;

export interface HistoryContentsStats {
  id: string;
  update_time: string;
  size: number;
  contents_active: components["schemas"]["HistoryActiveContentCounts"];
}

export interface HistorySummaryExtended extends HistorySummary, HistoryContentsStats {
  user_id: string | null;
}

export interface SelectableObjectStore extends ConcreteObjectStoreModel {
  object_store_id: string;
}

export type DatasetEntry = HDASummary | HDADetailed | HDAInaccessible;

export interface DCECollection extends DCESummary {
  element_type: "dataset_collection";
  object: DCObject;
}

export interface DCEDataset extends DCESummary {
  element_type: "hda";
  object: HDAObject;
}

export interface SubCollection extends DCObject {
  name: string;
  hdca_id: string;
}

export type CollectionEntry = HDCASummary | SubCollection;
export type HistoryItemSummary = HDASummary | HDCASummary;

// Utility functions
export function isHDA(entry?: HistoryItemSummary): entry is HDASummary {
  return entry !== undefined && "history_content_type" in entry && entry.history_content_type === "dataset";
}

export function isHDCA(entry?: HistoryItemSummary | CollectionEntry): entry is HDCASummary {
  return (
    entry !== undefined && "history_content_type" in entry && entry.history_content_type === "dataset_collection"
  );
}

export function isDCE(item: object): item is DCESummary {
  return item && "element_type" in item;
}

export function isCollectionElement(element: DCESummary): element is DCECollection {
  return element.element_type === "dataset_collection";
}

export function isDatasetElement(element: DCESummary): element is DCEDataset {
  return element.element_type === "hda";
}

export function hasDetails(entry: DatasetEntry): entry is HDADetailed {
  return "peek" in entry;
}

export function isInaccessible(entry: DatasetEntry): entry is HDAInaccessible {
  return "accessible" in entry && !entry.accessible;
}