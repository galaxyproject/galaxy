import { components } from "@/schema";

export type DatasetSummary = components["schemas"]["HDASummary"];
export type DatasetDetails = components["schemas"]["HDADetailed"];

export type HistoryContentItemBase = components["schemas"]["EncodedHistoryContentItem"];

export type DatasetEntry = DatasetSummary | DatasetDetails;
