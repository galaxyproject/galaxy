import type { components } from "@/api/schema/schema";

export type FetchPayload = components["schemas"]["FetchDataPayload"];
export type DataElementsTarget = components["schemas"]["DataElementsTarget"];
export type HdaDestination = components["schemas"]["HdaDestination"];
export type FileDataElement = components["schemas"]["FileDataElement"];
export type PastedDataElement = components["schemas"]["PastedDataElement"];
export type UrlDataElement = components["schemas"]["UrlDataElement"];
export type FetchDatasetHash = components["schemas"]["FetchDatasetHash"];

// Union of supported element sources for the basic (non-advanced) panel
export type UploadElement = FileDataElement | PastedDataElement | UrlDataElement;
